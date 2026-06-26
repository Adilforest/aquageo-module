"""Document text extraction + LLM field extraction (issue #22).

Excel/PDF -> text -> LLM structured extraction (schema from ObjectType) ->
draft Structure (with geom from coordinates). The LLM call goes through #21's
``extract_structured`` (mocked in tests — no real network call in CI).
"""
from __future__ import annotations

from django.contrib.gis.geos import Point

from catalog.models import Structure

from .llm import extract_structured

# Common (non-type-specific) fields we always try to extract.
COMMON_PROPERTIES = {
    "name_ru": {"type": "string"},
    "latitude": {"type": "number"},
    "longitude": {"type": "number"},
    "commissioning_year": {"type": "integer"},
    "responsible_org": {"type": "string"},
    "danger_level": {"type": "number"},
}
COMMON_KEYS = set(COMMON_PROPERTIES)


def excel_to_text(path: str) -> str:
    """Read an .xlsx into 'field: value' lines (and a flat join of all cells)."""
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    lines: list[str] = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            cells = [str(c).strip() for c in row if c is not None and str(c).strip()]
            if cells:
                lines.append(": ".join(cells) if len(cells) <= 3 else " ".join(cells))
    wb.close()
    return "\n".join(lines)


def pdf_to_text(path: str) -> str:
    """Extract the text layer from a PDF (OCR for scans is a future option)."""
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages)


def document_to_text(source_kind: str, path: str) -> str:
    if source_kind == "excel":
        return excel_to_text(path)
    if source_kind == "pdf":
        return pdf_to_text(path)
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def build_extraction_schema(object_type) -> dict:
    """Common fields + the object type's attribute schema."""
    props = dict(COMMON_PROPERTIES)
    props.update((object_type.schema or {}).get("properties", {}))
    return {"type": "object", "properties": props}


def derive_confidence(extracted: dict, text: str) -> dict:
    """Per-field confidence: explicit-in-text=high, present=medium, empty=low."""
    out = {}
    for key, value in extracted.items():
        if value in (None, ""):
            out[key] = "low"
        elif str(value) in text:
            out[key] = "high"
        else:
            out[key] = "medium"
    return out


def _draft_from_extract(object_type, extracted: dict, user) -> Structure:
    lat, lon = extracted.get("latitude"), extracted.get("longitude")
    geom = None
    try:
        if lat is not None and lon is not None:
            geom = Point(float(lon), float(lat), srid=4326)
    except (TypeError, ValueError):
        geom = None
    attrs = {k: v for k, v in extracted.items() if k not in COMMON_KEYS and v is not None}
    return Structure.objects.create(
        type=object_type,
        name_ru=extracted.get("name_ru") or f"{object_type.name_ru} (черновик)",
        geom=geom,
        status="draft",
        commissioning_year=extracted.get("commissioning_year"),
        responsible_org=extracted.get("responsible_org") or "",
        attributes=attrs,
        needs_geocoding=geom is None,
        created_by=user if getattr(user, "is_authenticated", False) else None,
    )


def run_parse(job, object_type, *, extractor=None):
    """Run the full pipeline for a ParseJob. Sets status done/error; never raises.

    ``extract_structured`` is looked up as a module global at call time so tests
    can patch ``ingestion.extract.extract_structured`` (no real LLM call).
    """
    from .models import ParseJob

    extract_fn = extractor if extractor is not None else extract_structured
    job.status = ParseJob.Status.PROCESSING
    job.save(update_fields=["status", "updated_at"])
    try:
        text = document_to_text(job.source_kind, job.file.path)
        if not text.strip():
            raise ValueError("Документ пуст или текст не распознан")
        schema = build_extraction_schema(object_type)
        extracted = extract_fn(text, schema)
        job.raw_extract = extracted
        job.confidence = derive_confidence(extracted, text)
        job.result_structure = _draft_from_extract(object_type, extracted, job.created_by)
        job.status = ParseJob.Status.DONE
        job.error_message = ""
    except Exception as exc:  # noqa: BLE001 — surface any failure as job error
        job.status = ParseJob.Status.ERROR
        job.error_message = str(exc)
    job.save()
    return job
