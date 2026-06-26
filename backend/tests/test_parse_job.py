"""ParseJob / document extraction tests — LLM mocked, NO real calls (#22)."""
from pathlib import Path
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from rest_framework.test import APIClient

from accounts.models import Role
from catalog.models import ObjectType
from ingestion.extract import run_parse
from ingestion.models import ParseJob

User = get_user_model()
SAMPLES = Path(settings.BASE_DIR) / "data" / "samples"

# What the (mocked) LLM "returns" — matches the sample documents.
MOCK_FIELDS = {
    "name_ru": "Гидропост Демо-Талас",
    "latitude": 43.123456,
    "longitude": 71.654321,
    "commissioning_year": 2018,
    "responsible_org": "Казводхоз (демо)",
    "danger_level": 350,
    "river": "Талас",
}


@pytest.fixture(scope="module", autouse=True)
def ensure_samples():
    if not (SAMPLES / "hydropost_sample.xlsx").exists():
        call_command("generate_sample_docs")


@pytest.fixture
def hydropost_type(db):
    return ObjectType.objects.create(
        code="hydropost", name_ru="Гидропост", geometry_kind="point",
        schema={"type": "object", "properties": {"river": {"type": "string"},
                                                  "datum_m": {"type": "number"}}},
    )


def make_job(kind, filename):
    content = (SAMPLES / filename).read_bytes()
    job = ParseJob.objects.create(source_kind=kind)
    job.file.save(filename, SimpleUploadedFile(filename, content), save=True)
    return job


@pytest.mark.django_db
def test_parse_xlsx_extracts_fields_and_geom(hydropost_type):
    job = make_job(ParseJob.SourceKind.EXCEL, "hydropost_sample.xlsx")
    with patch("ingestion.extract.extract_structured", return_value=dict(MOCK_FIELDS)) as m:
        run_parse(job, hydropost_type)
    job.refresh_from_db()
    assert job.status == ParseJob.Status.DONE
    assert job.raw_extract["name_ru"] == "Гидропост Демо-Талас"
    assert job.confidence  # per-field confidence filled
    # coordinates -> draft geometry
    draft = job.result_structure
    assert draft is not None and draft.status == "draft"
    assert draft.geom is not None and draft.geom.geom_type == "Point"
    assert round(draft.geom.x, 4) == 71.6543
    assert draft.attributes.get("river") == "Талас"
    assert m.call_count == 1  # exactly one (mocked) LLM call


@pytest.mark.django_db
def test_parse_pdf_extracts_text(hydropost_type):
    job = make_job(ParseJob.SourceKind.PDF, "hydropost_passport.pdf")
    with patch("ingestion.extract.extract_structured", return_value=dict(MOCK_FIELDS)):
        run_parse(job, hydropost_type)
    job.refresh_from_db()
    assert job.status == ParseJob.Status.DONE
    assert job.raw_extract["river"] == "Талас"
    # the sample PDF carries a real text layer -> high confidence for present values
    assert job.confidence["name_ru"] == "high"


@pytest.mark.django_db
def test_empty_or_invalid_file_sets_error(hydropost_type):
    job = ParseJob.objects.create(source_kind=ParseJob.SourceKind.EXCEL)
    job.file.save("bad.xlsx", SimpleUploadedFile("bad.xlsx", b"not a real xlsx"), save=True)
    with patch("ingestion.extract.extract_structured", return_value=dict(MOCK_FIELDS)):
        run_parse(job, hydropost_type)
    job.refresh_from_db()
    assert job.status == ParseJob.Status.ERROR
    assert job.error_message  # readable message, no crash
    assert job.result_structure is None


@pytest.mark.django_db
def test_parse_draft_excluded_from_map_and_list(hydropost_type):
    job = make_job(ParseJob.SourceKind.EXCEL, "hydropost_sample.xlsx")
    with patch("ingestion.extract.extract_structured", return_value=dict(MOCK_FIELDS)):
        run_parse(job, hydropost_type)
    draft_id = str(job.result_structure_id)
    api = APIClient()
    geo = api.get("/api/v1/structures/geojson/").data
    assert all(f["properties"]["id"] != draft_id for f in geo["features"])
    listed = api.get("/api/v1/structures/").data
    assert all(r["id"] != draft_id for r in listed["results"])
    # but still retrievable by id (for the review screen #24)
    assert api.get(f"/api/v1/structures/{draft_id}/").status_code == 200


@pytest.mark.django_db
def test_viewer_cannot_create_parse_job(hydropost_type):
    User.objects.create_user("v", password="p", role=Role.VIEWER)
    c = APIClient()
    token = APIClient().post(
        "/api/v1/auth/login/", {"username": "v", "password": "p"}, format="json"
    ).data["access"]
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    content = (SAMPLES / "hydropost_sample.xlsx").read_bytes()
    resp = c.post(
        "/api/v1/parse-jobs/",
        {"object_type": "hydropost",
         "file": SimpleUploadedFile("s.xlsx", content)},
        format="multipart",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_engineer_create_parse_job_api(hydropost_type):
    User.objects.create_user("e", password="p", role=Role.ENGINEER)
    c = APIClient()
    token = APIClient().post(
        "/api/v1/auth/login/", {"username": "e", "password": "p"}, format="json"
    ).data["access"]
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    content = (SAMPLES / "hydropost_sample.xlsx").read_bytes()
    with patch("ingestion.extract.extract_structured", return_value=dict(MOCK_FIELDS)):
        resp = c.post(
            "/api/v1/parse-jobs/",
            {"object_type": "hydropost",
             "file": SimpleUploadedFile("s.xlsx", content)},
            format="multipart",
        )
    assert resp.status_code == 201, resp.data
    assert resp.data["status"] == "done"
    assert resp.data["raw_extract"]["river"] == "Талас"
