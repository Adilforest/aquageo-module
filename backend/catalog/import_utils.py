"""Helpers for the data importer (issue #8).

Kept separate from the management command so the mapping logic is unit-testable.
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import date, timedelta

import ijson

# Jambyl / Shu-Talas approximate bounding box: lon_min, lat_min, lon_max, lat_max.
DEFAULT_BBOX = (69.0, 42.0, 76.0, 46.0)

# CSV "bassein" value -> seeded Basin.name_ru.
BASSEIN_MAP = {
    "Арало-Сырдарья": "Арало-Сырдарьинский",
    "Балхаш-Алаколь": "Балхаш-Алакольский",
    "Есиль": "Есильский",
    "Иртыш": "Ертисский",
    "Нура-Сарысу": "Нура-Сарысуский",
    "Тобол-Торгай": "Тобол-Тургайский",
    "Урало-Каспий": "Жайык-Каспийский",
    "Шу-Талас": "Шу-Таласский",
}

# Overpass point tags -> ObjectType.code (DATA_NOTES.md §2).
OVERPASS_WATERWAY = {"dam": "dam", "weir": "spillway", "lock_gate": "lock"}
OVERPASS_MAN_MADE = {"dyke": "dike"}


def iter_features(path: str):
    """Yield GeoJSON features from a .geojson file or a .zip containing one.

    Uses ijson so multi-hundred-MB country-wide files stream instead of loading
    entirely into memory.
    """
    if path.endswith(".zip"):
        zf = zipfile.ZipFile(path)
        member = next(n for n in zf.namelist() if n.endswith(".geojson"))
        fh = zf.open(member)
        try:
            yield from ijson.items(fh, "features.item")
        finally:
            fh.close()
            zf.close()
    else:
        with open(path, "rb") as fh:
            yield from ijson.items(fh, "features.item")


def first_point(geometry: dict) -> tuple[float, float] | None:
    """Return a representative (lon, lat) for any geometry, or None."""
    coords = geometry.get("coordinates")
    if not coords:
        return None
    while isinstance(coords[0], (list, tuple)):
        coords = coords[0]
    return float(coords[0]), float(coords[1])


def in_bbox(lon: float, lat: float, bbox=DEFAULT_BBOX) -> bool:
    lon_min, lat_min, lon_max, lat_max = bbox
    return lon_min <= lon <= lon_max and lat_min <= lat <= lat_max


def geometry_in_bbox(geometry: dict, bbox=DEFAULT_BBOX) -> bool:
    pt = first_point(geometry)
    return bool(pt) and in_bbox(pt[0], pt[1], bbox)


def geom_to_geos(geometry: dict):
    """Build a GEOSGeometry (srid 4326) from a GeoJSON geometry dict."""
    from django.contrib.gis.geos import GEOSGeometry

    # ijson yields Decimal coordinates; default=float makes them JSON-serialisable.
    return GEOSGeometry(json.dumps(geometry, default=float), srid=4326)


def name_from(props: dict) -> dict:
    """Extract localized names from OSM-style properties."""
    return {
        "name_ru": (props.get("name:ru") or props.get("name") or "").strip(),
        "name_kk": (props.get("name:kk") or "").strip(),
        "name_en": (props.get("name:en") or "").strip(),
    }


def plausible_condition(key: str) -> dict:
    """Deterministically generate plausible wear/condition/inspection for demo.

    The sources lack these fields (CLAUDE.md §13). Values are derived from a hash
    of a stable key, so they are reproducible across runs (not random).
    """
    h = int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16)
    wear = h % 85  # 0..84 %
    if wear < 30:
        condition = "serviceable"
    elif wear < 55:
        condition = "monitoring"
    elif wear < 72:
        condition = "repair"
    else:
        condition = "emergency"
    year = 1960 + (h // 97) % 62  # 1960..2021
    days_ago = (h // 13) % 1095  # within ~3 years
    inspected_at = date(2026, 1, 1) - timedelta(days=days_ago)
    return {
        "wear_percent": wear,
        "condition_status": condition,
        "commissioning_year": year,
        "inspected_at": inspected_at,
    }
