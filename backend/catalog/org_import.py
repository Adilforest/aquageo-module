"""Parsing/import helpers for the organizers' canal dataset (issue #65).

Objects are imported WITHOUT geometry and flagged ``needs_geocoding=True`` —
they appear in the catalog but not on the map until geocoded/verified.

Column mapping (0-based) of the "каналы" sheet -> Structure(type=canal).
Parsing is kept pure (``parse_row``) so it is unit-testable without an .xls file.
"""
from __future__ import annotations

from decimal import Decimal


def _num(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _str(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_row(row: list, index: int) -> dict | None:
    """Map one data row to Structure fields.

    ``index`` is the absolute sheet row index — used for a globally-unique
    source_key, because the № column restarts per "Группа объектов" group.
    Returns None for empty rows and group/subtotal rows (non-numeric № column).
    """
    if not row:
        return None
    raw_n = _num(row[0])
    if raw_n is None:  # group header / subtotal / blank row
        return None
    n = int(raw_n)

    attrs: dict = {}

    def put(key, val):
        if val is not None and val != "":
            attrs[key] = val

    put("water_source", _str(row[2]) or None)
    put("capacity_m3s", _num(row[3]))
    put("length_km", _num(row[4]))
    put("length_earthen_km", _num(row[5]))
    put("length_lined_km", _num(row[6]))
    put("efficiency_design", _num(row[14]))
    put("efficiency_actual", _num(row[15]))
    put("served_districts", _str(row[16]) or None)
    put("rural_okrug", _str(row[17]) or None)
    put("reported_condition", _str(row[19]) or None)

    wear_raw = _num(row[18])
    wear = None
    if wear_raw is not None:
        d = Decimal(str(wear_raw))
        if d <= 1:  # file stores a 0..1 fraction
            d *= 100
        wear = d.quantize(Decimal("0.01"))  # wear_percent is Decimal(max 2 dp)

    year = None
    if _str(row[1]):
        year = int(float(row[1]))

    attrs["dataset_no"] = n  # in-group number (not unique across groups)

    served = _str(row[16])
    name = f"Канал (org-xls #{n})" + (f", {served}" if served else "")

    source_key = f"org-xls:canal:{index}"
    attrs["source_key"] = source_key

    return {
        "source_key": source_key,
        "name_ru": name,
        "commissioning_year": year,
        "wear_percent": wear,
        "cadastral_number": _str(row[20]),
        "state_act": _str(row[21]),
        "attributes": attrs,
    }


def import_rows(rows: list, row_offset: int = 7) -> tuple[int, int]:
    """Create canal structures from parsed rows. Returns (created, skipped).

    ``row_offset`` is the absolute index of the first row (skiprows), so
    source_keys match the file even when called with a slice.
    """
    from .models import ObjectType, Structure

    canal = ObjectType.objects.get(code="canal")
    created = 0
    skipped = 0
    for i, row in enumerate(rows):
        fields = parse_row(row, row_offset + i)
        if fields is None:
            continue
        if Structure.objects.filter(attributes__source_key=fields["source_key"]).exists():
            skipped += 1
            continue
        structure = Structure(
            type=canal,
            geom=None,
            needs_geocoding=True,
            name_ru=fields["name_ru"],
            commissioning_year=fields["commissioning_year"],
            wear_percent=fields["wear_percent"],
            cadastral_number=fields["cadastral_number"],
            state_act=fields["state_act"],
            attributes=fields["attributes"],
        )
        # Validates attributes against the canal JSON-schema (Structure.clean()).
        structure.full_clean(exclude=["geom"])
        structure.save()
        created += 1
    return created, skipped
