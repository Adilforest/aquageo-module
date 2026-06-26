"""Import Jambyl hydro objects from qazsu CSV, Overpass and HDX GeoJSON.

Mapping per DATA_NOTES.md:
  - qazsu CSV       -> Structure(hydropost), Point
  - Overpass points -> Structure(dam/spillway/lock/dike)
  - HDX lines       -> Structure(canal); rivers/streams -> WaterBody (named)
  - HDX polygons    -> WaterBody(reservoir/lake)

Big HDX files are filtered by bounding box while streaming (ijson), never loaded
whole. Missing wear/condition/inspection date are generated plausibly (CLAUDE §13).
"""
import csv
from pathlib import Path

from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.import_utils import (
    BASSEIN_MAP,
    DEFAULT_BBOX,
    OVERPASS_MAN_MADE,
    OVERPASS_WATERWAY,
    first_point,
    geom_to_geos,
    geometry_in_bbox,
    in_bbox,
    iter_features,
    name_from,
    plausible_condition,
)
from catalog.models import (
    AdminUnit,
    Basin,
    Inspection,
    ObjectType,
    Structure,
    WaterBody,
)

DATA_DIR = Path(settings.BASE_DIR) / "data"


class Command(BaseCommand):
    help = "Import hydro structures and water bodies for the Jambyl region."

    def add_arguments(self, parser):
        parser.add_argument("--hydroposts", default=str(DATA_DIR / "qazsu_hydroposts_334.csv"))
        parser.add_argument("--overpass", default=str(DATA_DIR / "export.geojson"))
        parser.add_argument(
            "--lines", default=str(DATA_DIR / "hotosm_kaz_waterways_lines_geojson.zip")
        )
        parser.add_argument(
            "--polygons", default=str(DATA_DIR / "hotosm_kaz_waterways_polygons_geojson.zip")
        )
        parser.add_argument("--bbox", default=",".join(str(x) for x in DEFAULT_BBOX))
        parser.add_argument("--max-canals", type=int, default=0, help="0 = unlimited")
        parser.add_argument("--skip-lines", action="store_true")
        parser.add_argument("--skip-polygons", action="store_true")

    def handle(self, *args, **opts):
        self.bbox = tuple(float(x) for x in opts["bbox"].split(","))
        if len(self.bbox) != 4:
            raise CommandError("--bbox must be 'lon_min,lat_min,lon_max,lat_max'")

        self.types = {t.code: t for t in ObjectType.objects.all()}
        if "hydropost" not in self.types:
            raise CommandError("Reference data missing — run seed_reference first.")
        self.basins = {b.name_ru: b for b in Basin.objects.all()}
        self.shu_talas = self.basins.get("Шу-Таласский")
        self.region = AdminUnit.objects.filter(kato="31").first()

        self.created = {"structures": 0, "water_bodies": 0}

        self._import_hydroposts(opts["hydroposts"])
        self._import_overpass(opts["overpass"])
        if not opts["skip_lines"]:
            self._import_lines(opts["lines"], opts["max_canals"])
        if not opts["skip_polygons"]:
            self._import_polygons(opts["polygons"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {self.created['structures']} structures and "
                f"{self.created['water_bodies']} water bodies. "
                f"Totals now: {Structure.objects.count()} structures, "
                f"{WaterBody.objects.count()} water bodies."
            )
        )

    # --- helpers ----------------------------------------------------------
    def _upsert_structure(self, source_key, type_code, names, geom, basin, admin, extra=None):
        if Structure.objects.filter(attributes__source_key=source_key).exists():
            return False
        cond = plausible_condition(source_key)
        attrs = {"source_key": source_key}
        if extra:
            attrs.update(extra)
        with transaction.atomic():
            s = Structure.objects.create(
                type=self.types[type_code],
                name_ru=names["name_ru"] or f"{self.types[type_code].name_ru} {source_key}",
                name_kk=names.get("name_kk", ""),
                name_en=names.get("name_en", ""),
                geom=geom,
                basin=basin,
                admin_unit=admin,
                wear_percent=cond["wear_percent"],
                condition_status=cond["condition_status"],
                commissioning_year=cond["commissioning_year"],
                attributes=attrs,
            )
            Inspection.objects.create(
                structure=s,
                inspected_at=cond["inspected_at"],
                inspector="Импорт (демо)",
                condition_observed=cond["condition_status"],
                wear_percent=cond["wear_percent"],
            )
        self.created["structures"] += 1
        return True

    def _upsert_waterbody(self, name_ru, kind, geom, basin, name_kk="", name_en=""):
        wb, created = WaterBody.objects.get_or_create(
            name_ru=name_ru,
            kind=kind,
            defaults={"name_kk": name_kk, "name_en": name_en, "basin": basin, "geom": geom},
        )
        if created:
            self.created["water_bodies"] += 1
        elif wb.geom is None and geom is not None:
            # Enrich a seeded river (Талас/Шу/Аса) with real geometry.
            wb.geom = geom
            if basin and wb.basin is None:
                wb.basin = basin
            wb.save(update_fields=["geom", "basin"])
        return wb

    # --- sources ----------------------------------------------------------
    def _import_hydroposts(self, path):
        if not Path(path).exists():
            self.stdout.write(self.style.WARNING(f"hydroposts file not found: {path}"))
            return
        with open(path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                try:
                    lon, lat = float(row["longitude"]), float(row["latitude"])
                except (ValueError, KeyError, TypeError):
                    continue
                basin = self.basins.get(BASSEIN_MAP.get(row.get("bassein", "")))
                admin = self.region if "Жамбыл" in row.get("region", "") else None
                self._upsert_structure(
                    f"qazsu:{row['id']}",
                    "hydropost",
                    {"name_ru": row.get("name", "").strip()},
                    Point(lon, lat, srid=4326),
                    basin,
                    admin,
                    extra={
                        "river": row.get("name", ""),
                        "danger_level": row.get("danger_level", ""),
                        "level_mean": row.get("level_mean", ""),
                        "water_temp": row.get("water_temp", ""),
                        "date": row.get("date", ""),
                    },
                )

    def _import_overpass(self, path):
        if not Path(path).exists():
            self.stdout.write(self.style.WARNING(f"overpass file not found: {path}"))
            return
        for feat in iter_features(path):
            geom = feat.get("geometry") or {}
            if geom.get("type") != "Point":
                continue
            props = feat.get("properties", {})
            code = OVERPASS_WATERWAY.get(props.get("waterway")) or OVERPASS_MAN_MADE.get(
                props.get("man_made")
            )
            if not code:
                continue
            pt = first_point(geom)
            if not pt or not in_bbox(pt[0], pt[1], self.bbox):
                continue
            fid = feat.get("id") or props.get("@id") or f"{pt[0]},{pt[1]}"
            self._upsert_structure(
                f"overpass:{fid}",
                code,
                name_from(props),
                geom_to_geos(geom),
                self.shu_talas,
                self.region,
            )

    def _import_lines(self, path, max_canals):
        if not Path(path).exists():
            self.stdout.write(self.style.WARNING(f"lines file not found: {path}"))
            return
        seen = 0
        canals = 0
        for feat in iter_features(path):
            seen += 1
            if seen % 50000 == 0:
                self.stdout.write(f"  ...scanned {seen} line features")
            geom = feat.get("geometry") or {}
            props = feat.get("properties", {})
            ww = props.get("waterway")
            if ww not in ("canal", "river", "stream"):
                continue
            if not geometry_in_bbox(geom, self.bbox):
                continue
            if ww == "canal":
                if max_canals and canals >= max_canals:
                    continue
                osm_id = props.get("osm_id")
                if self._upsert_structure(
                    f"hdxline:{osm_id}",
                    "canal",
                    name_from(props),
                    geom_to_geos(geom),
                    self.shu_talas,
                    self.region,
                    extra={"osm_id": osm_id},
                ):
                    canals += 1
            else:
                names = name_from(props)
                if not names["name_ru"]:
                    continue  # only named rivers/streams become WaterBodies
                kind = WaterBody.Kind.RIVER if ww == "river" else WaterBody.Kind.STREAM
                self._upsert_waterbody(
                    names["name_ru"], kind, geom_to_geos(geom), self.shu_talas,
                    names["name_kk"], names["name_en"],
                )

    def _import_polygons(self, path):
        if not Path(path).exists():
            self.stdout.write(self.style.WARNING(f"polygons file not found: {path}"))
            return
        for feat in iter_features(path):
            props = feat.get("properties", {})
            if props.get("natural") != "water":
                continue
            water = props.get("water")
            if water not in ("reservoir", "lake"):
                continue
            geom = feat.get("geometry") or {}
            if not geometry_in_bbox(geom, self.bbox):
                continue
            names = name_from(props)
            kind = WaterBody.Kind.RESERVOIR if water == "reservoir" else WaterBody.Kind.LAKE
            label = "Водохранилище" if kind == WaterBody.Kind.RESERVOIR else "Озеро"
            name_ru = names["name_ru"] or f"{label} (OSM {props.get('osm_id')})"
            self._upsert_waterbody(
                name_ru, kind, geom_to_geos(geom), self.shu_talas,
                names["name_kk"], names["name_en"],
            )
