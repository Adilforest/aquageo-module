"""Seed catalog reference data: object types, basins, Jambyl KATO, rivers.

Idempotent — safe to run repeatedly (uses update_or_create).
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import AdminUnit, Basin, ObjectType, WaterBody

# --- Object types with attribute JSON schemas (CLAUDE.md §5) ----------------
OBJECT_TYPES = [
    ("canal", "Канал", "Канал", "Canal", "line", {
        "type": "object",
        "properties": {
            "length_km": {"type": "number"},
            "throughput_m3s": {"type": "number"},
            "lined": {"type": "boolean"},
            # Fields from the organizers' dataset (issue #65).
            "water_source": {"type": "string"},
            "capacity_m3s": {"type": "number"},
            "length_earthen_km": {"type": "number"},
            "length_lined_km": {"type": "number"},
            "efficiency_design": {"type": "number"},
            "efficiency_actual": {"type": "number"},
            "served_districts": {"type": "string"},
            "rural_okrug": {"type": "string"},
            "reported_condition": {"type": "string"},
        },
    }),
    ("hydropost", "Гидропост", "Гидробекет", "Hydropost", "point", {
        "type": "object",
        "properties": {
            "datum_m": {"type": "number"},
            "river": {"type": "string"},
        },
    }),
    ("lock", "Шлюз", "Шлюз", "Lock", "point", {
        "type": "object",
        "properties": {"chambers": {"type": "integer"}},
    }),
    ("water_intake", "Водозабор", "Су алу", "Water intake", "point", {
        "type": "object",
        "properties": {"capacity_m3s": {"type": "number"}},
    }),
    ("pumping_station", "Насосная станция", "Сорғы станциясы", "Pumping station", "point", {
        "type": "object",
        "properties": {"power_kw": {"type": "number"}, "pumps": {"type": "integer"}},
    }),
    ("dam", "Плотина", "Бөген", "Dam", "point", {
        "type": "object",
        "properties": {
            "height_m": {"type": "number"},
            "crest_length_m": {"type": "number"},
            "material": {"type": "string"},
        },
    }),
    ("dike", "Дамба", "Дамба", "Dike", "line", {
        "type": "object",
        "properties": {"length_m": {"type": "number"}, "height_m": {"type": "number"}},
    }),
    ("reservoir", "Водохранилище", "Су қоймасы", "Reservoir", "polygon", {
        "type": "object",
        "properties": {"volume_mln_m3": {"type": "number"}, "area_km2": {"type": "number"}},
    }),
    ("hydro_unit", "Гидроузел", "Гидротүйін", "Hydro unit", "point", {
        "type": "object",
        "properties": {"river": {"type": "string"}},
    }),
    ("spillway", "Водосброс", "Су төгу", "Spillway", "point", {
        "type": "object",
        "properties": {"capacity_m3s": {"type": "number"}},
    }),
    ("pond", "Пруд", "Тоған", "Pond", "polygon", {
        "type": "object",
        "properties": {"area_km2": {"type": "number"}},
    }),
]

# --- Eight water-management basins of Kazakhstan ----------------------------
BASINS = [
    ("Арало-Сырдарьинский", "Арал-Сырдария", "Aral-Syrdarya"),
    ("Балхаш-Алакольский", "Балқаш-Алакөл", "Balkhash-Alakol"),
    ("Шу-Таласский", "Шу-Талас", "Shu-Talas"),
    ("Есильский", "Есіл", "Esil"),
    ("Ертисский", "Ертіс", "Yertis"),
    ("Жайык-Каспийский", "Жайық-Каспий", "Zhaiyk-Caspian"),
    ("Нура-Сарысуский", "Нұра-Сарысу", "Nura-Sarysu"),
    ("Тобол-Тургайский", "Тобыл-Торғай", "Tobol-Turgai"),
]

# --- Jambyl region KATO hierarchy: region -> districts -> sample okrugs ------
REGION = ("31", "Жамбылская область", "Жамбыл облысы", "Jambyl region")
DISTRICTS = [
    ("3102", "город Тараз", "Тараз қаласы", "Taraz city"),
    ("3110", "Байзакский район", "Байзақ ауданы", "Baizak district"),
    ("3114", "Жамбылский район", "Жамбыл ауданы", "Jambyl district"),
    ("3118", "Жуалынский район", "Жуалы ауданы", "Zhualy district"),
    ("3122", "Кордайский район", "Қордай ауданы", "Korday district"),
    ("3126", "Меркенский район", "Меркі ауданы", "Merke district"),
    ("3130", "Мойынкумский район", "Мойынқұм ауданы", "Moiynkum district"),
    ("3134", "район Турара Рыскулова", "Т. Рысқұлов ауданы", "T. Ryskulov district"),
    ("3138", "Сарысуский район", "Сарысу ауданы", "Sarysu district"),
    ("3142", "Таласский район", "Талас ауданы", "Talas district"),
    ("3146", "Шуский район", "Шу ауданы", "Shu district"),
]
# A couple of rural okrugs under Korday (3122) to demonstrate the okrug level.
OKRUGS = [
    ("312201", "Кордайский сельский округ", "Қордай ауылдық округі",
     "Korday rural okrug", "3122"),
    ("312202", "Сортюбинский сельский округ", "Сортөбе ауылдық округі",
     "Sortobe rural okrug", "3122"),
]

# --- Rivers of the Shu-Talas basin (geometry added by the importer, #8) ------
RIVERS = [
    ("Талас", "Талас", "Talas"),
    ("Шу", "Шу", "Shu"),
    ("Аса", "Аса", "Asa"),
]


class Command(BaseCommand):
    help = "Seed reference data (object types, basins, Jambyl KATO, rivers)."

    @transaction.atomic
    def handle(self, *args, **options):
        for code, ru, kk, en, kind, schema in OBJECT_TYPES:
            ObjectType.objects.update_or_create(
                code=code,
                defaults={
                    "name_ru": ru, "name_kk": kk, "name_en": en,
                    "geometry_kind": kind, "schema": schema,
                },
            )

        basins = {}
        for ru, kk, en in BASINS:
            basin, _ = Basin.objects.update_or_create(
                name_ru=ru, defaults={"name_kk": kk, "name_en": en}
            )
            basins[ru] = basin

        region, _ = AdminUnit.objects.update_or_create(
            kato=REGION[0],
            defaults={
                "name_ru": REGION[1], "name_kk": REGION[2], "name_en": REGION[3],
                "level": AdminUnit.Level.REGION, "parent": None,
            },
        )
        districts = {}
        for kato, ru, kk, en in DISTRICTS:
            d, _ = AdminUnit.objects.update_or_create(
                kato=kato,
                defaults={
                    "name_ru": ru, "name_kk": kk, "name_en": en,
                    "level": AdminUnit.Level.DISTRICT, "parent": region,
                },
            )
            districts[kato] = d
        for kato, ru, kk, en, parent_kato in OKRUGS:
            AdminUnit.objects.update_or_create(
                kato=kato,
                defaults={
                    "name_ru": ru, "name_kk": kk, "name_en": en,
                    "level": AdminUnit.Level.OKRUG, "parent": districts[parent_kato],
                },
            )

        shu_talas = basins["Шу-Таласский"]
        for ru, kk, en in RIVERS:
            WaterBody.objects.update_or_create(
                name_ru=ru,
                kind=WaterBody.Kind.RIVER,
                defaults={"name_kk": kk, "name_en": en, "basin": shu_talas},
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded: {ObjectType.objects.count()} object types, "
                f"{Basin.objects.count()} basins, "
                f"{AdminUnit.objects.count()} admin units, "
                f"{WaterBody.objects.count()} water bodies."
            )
        )
