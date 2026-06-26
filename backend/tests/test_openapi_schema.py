"""OpenAPI schema completeness tests (issue #15)."""
import pytest
from django.test import Client


@pytest.fixture(scope="module")
def schema():
    resp = Client().get("/api/v1/schema/", {"format": "json"})
    assert resp.status_code == 200
    return resp.json()


KEY_PATHS = [
    "/api/v1/structures/",
    "/api/v1/structures/{id}/",
    "/api/v1/structures/geojson/",
    "/api/v1/structures/{id}/readings/",
    "/api/v1/stats/by-type/",
    "/api/v1/stats/by-condition/",
    "/api/v1/stats/by-territory/",
    "/api/v1/stats/risk-summary/",
    "/api/v1/stats/level-timeseries/",
    "/api/v1/reports/condition-summary/",
    "/api/v1/basins/",
    "/api/v1/admin-units/",
    "/api/v1/object-types/",
    "/api/v1/water-bodies/",
    "/api/v1/auth/login/",
    "/api/v1/auth/refresh/",
    "/api/v1/auth/me/",
]


def test_schema_is_valid_openapi(schema):
    assert schema["openapi"].startswith("3.")
    assert schema["info"]["title"] == "AquaGeo API"
    assert "paths" in schema and schema["paths"]


@pytest.mark.parametrize("path", KEY_PATHS)
def test_key_paths_present(schema, path):
    assert path in schema["paths"], f"{path} missing from schema"


def test_list_documents_multivalue_condition_param(schema):
    params = schema["paths"]["/api/v1/structures/"]["get"]["parameters"]
    names = {p["name"] for p in params}
    assert "condition" in names
    assert "type" in names
    assert "needs_geocoding" in names


def test_swagger_and_redoc_routes_present(schema):
    # both docs UIs are wired (resolvable view names exist)
    from django.urls import reverse
    assert reverse("swagger-ui") == "/api/v1/schema/swagger-ui/"
    assert reverse("redoc") == "/api/v1/schema/redoc/"
