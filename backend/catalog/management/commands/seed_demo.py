"""Seed plausible demo structures for the live map (no external data files).

The open-source importers (import_data / import_org_dataset) need files under
data/ that are not shipped in the image. For demos we instead create a compact,
realistic set of Jambyl (Shu-Talas basin) objects programmatically.

Idempotent — uses update_or_create keyed on (type, name_ru). Wear/condition/
commissioning are derived deterministically via plausible_condition (CLAUDE §13).
"""
from django.contrib.gis.geos import LineString, Point, Polygon
from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.import_utils import plausible_condition
from catalog.models import AdminUnit, Basin, Inspection, ObjectType, Structure

# type, name_ru, name_kk, name_en, geom_kind, coords, significance
#   geom_kind: "point" -> (lon, lat); "line" -> [(lon,lat), ...];
#              "poly"  -> [(lon,lat), ...] ring (auto-closed)
OBJECTS = [
    ("hydropost", "Гидропост Тараз", "Тараз гидробекеті", "Taraz hydropost",
     "point", (71.40, 42.90), "regional"),
    ("hydropost", "Гидропост Аса", "Аса гидробекеті", "Asa hydropost",
     "point", (71.20, 43.20), "regional"),
    ("hydropost", "Гидропост Талас", "Талас гидробекеті", "Talas hydropost",
     "point", (70.80, 42.80), "regional"),
    ("hydropost", "Гидропост Шу", "Шу гидробекеті", "Shu hydropost",
     "point", (73.76, 43.60), "regional"),
    ("hydropost", "Гидропост Мерке", "Мерке гидробекеті", "Merke hydropost",
     "point", (73.18, 42.87), "district"),
    ("hydro_unit", "Таласский гидроузел", "Талас гидротүйіні", "Talas hydronode",
     "point", (70.85, 42.78), "republican"),
    ("hydro_unit", "Ассинский гидроузел", "Аса гидротүйіні", "Assa hydronode",
     "point", (71.30, 43.30), "regional"),
    ("hydro_unit", "Фурмановский гидроузел", "Фурманов гидротүйіні", "Furmanov hydronode",
     "point", (71.10, 42.95), "regional"),
    ("dam", "Плотина Тасоткель", "Тасөткел бөгеті", "Tasotkel dam",
     "point", (73.55, 43.78), "republican"),
    ("reservoir", "Тасоткельское водохранилище", "Тасөткел су қоймасы", "Tasotkel reservoir",
     "poly", [(73.50, 43.74), (73.62, 43.74), (73.62, 43.82), (73.50, 43.82)], "republican"),
    ("dam", "Плотина Терс-Ащибулак", "Терісащыбұлақ бөгеті", "Ters-Ashibulak dam",
     "point", (70.30, 42.95), "republican"),
    ("reservoir", "Терс-Ащибулакское водохранилище", "Терісащыбұлақ су қоймасы", "Ters-Ashibulak reservoir",
     "poly", [(70.26, 42.92), (70.35, 42.92), (70.35, 42.99), (70.26, 42.99)], "regional"),
    ("canal", "Большой Таласский канал", "Үлкен Талас каналы", "Big Talas canal",
     "line", [(70.86, 42.79), (71.05, 42.85), (71.25, 42.90)], "regional"),
    ("canal", "Ассинский магистральный канал", "Аса магистральдық каналы", "Assa main canal",
     "line", [(71.28, 43.28), (71.40, 43.32), (71.55, 43.35)], "district"),
    ("lock", "Шлюз Тасоткель", "Тасөткел шлюзі", "Tasotkel lock",
     "point", (73.54, 43.77), "district"),
    ("spillway", "Водосброс Тасоткель", "Тасөткел су ағызғышы", "Tasotkel spillway",
     "point", (73.56, 43.79), "district"),
    ("pumping_station", "Насосная станция Мерке", "Мерке сорғы стансасы", "Merke pumping station",
     "point", (73.17, 42.88), "district"),
    ("water_intake", "Водозабор Талас", "Талас су тартқышы", "Talas water intake",
     "point", (70.83, 42.82), "district"),
    ("dike", "Дамба Аса", "Аса дамбасы", "Assa dike",
     "point", (71.22, 43.22), "local"),
    ("pond", "Пруд Сарыкемер", "Сарыкемер тоғаны", "Sarykemer pond",
     "poly", [(71.48, 42.98), (71.54, 42.98), (71.54, 43.03), (71.48, 43.03)], "local"),
]


def _geom(kind, coords):
    if kind == "point":
        return Point(coords[0], coords[1], srid=4326)
    if kind == "line":
        return LineString(coords, srid=4326)
    ring = list(coords) + [coords[0]]  # close polygon
    return Polygon(ring, srid=4326)


class Command(BaseCommand):
    help = "Create a compact set of plausible Jambyl demo structures for the map."

    @transaction.atomic
    def handle(self, *args, **opts):
        basin = Basin.objects.filter(name_ru="Шу-Таласский").first()
        region = AdminUnit.objects.filter(kato="31").first()
        if basin is None or region is None:
            self.stderr.write("Run seed_reference first (basin/admin unit missing).")
            return

        created = updated = 0
        for code, ru, kk, en, kind, coords, sig in OBJECTS:
            ot = ObjectType.objects.filter(code=code).first()
            if ot is None:
                continue
            cond = plausible_condition(ru)
            obj, was_created = Structure.objects.update_or_create(
                type=ot,
                name_ru=ru,
                defaults={
                    "name_kk": kk,
                    "name_en": en,
                    "geom": _geom(kind, coords),
                    "basin": basin,
                    "admin_unit": region,
                    "significance": sig,
                    "status": "published",
                    "condition_status": cond["condition_status"],
                    "wear_percent": cond["wear_percent"],
                    "commissioning_year": cond["commissioning_year"],
                    "responsible_org": "Жамбылский филиал РГП «Казводхоз»",
                    "needs_geocoding": False,
                },
            )
            created += int(was_created)
            updated += int(not was_created)
            Inspection.objects.update_or_create(
                structure=obj,
                inspected_at=cond["inspected_at"],
                defaults={
                    "inspector": "Демо-инспекция",
                    "condition_observed": cond["condition_status"],
                    "wear_percent": cond["wear_percent"],
                    "notes": "Сгенерировано для демонстрации.",
                },
            )

        self.stdout.write(self.style.SUCCESS(
            f"Demo structures: created {created}, updated {updated}, "
            f"total {Structure.objects.count()}."
        ))
