"""Smoke tests for the OpenAPI schema and docs endpoints.

These intentionally avoid the database so CI runs a real (not stub) test even
before any models/data exist.
"""
from django.test import Client
from django.urls import resolve, reverse
from drf_spectacular.views import SpectacularRedocView, SpectacularSwaggerView


def test_openapi_schema_endpoint_returns_200():
    resp = Client().get("/api/v1/schema/")
    assert resp.status_code == 200
    assert resp.content  # non-empty OpenAPI document


def test_swagger_ui_route_is_wired():
    assert reverse("swagger-ui") == "/api/v1/schema/swagger-ui/"
    assert resolve("/api/v1/schema/swagger-ui/").func.cls is SpectacularSwaggerView


def test_redoc_route_is_wired():
    assert reverse("redoc") == "/api/v1/schema/redoc/"
    assert resolve("/api/v1/schema/redoc/").func.cls is SpectacularRedocView
