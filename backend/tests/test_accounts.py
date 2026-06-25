"""Auth + RBAC tests (require the database; run on PostGIS in CI)."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from accounts.models import Role

User = get_user_model()

LOGIN_URL = "/api/v1/auth/login/"
REFRESH_URL = "/api/v1/auth/refresh/"
ME_URL = "/api/v1/auth/me/"
MANAGER_URL = "/api/v1/auth/manager-check/"

PASSWORD = "s3cret-pass-123"


def make_user(username, role=Role.VIEWER, **kwargs):
    return User.objects.create_user(
        username=username, password=PASSWORD, role=role, **kwargs
    )


@pytest.fixture
def api():
    return APIClient()


def auth(api, access):
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return api


@pytest.mark.django_db
def test_default_role_is_viewer():
    user = make_user("plain")
    assert user.role == Role.VIEWER


@pytest.mark.django_db
def test_login_returns_token_pair(api):
    make_user("engineer1", role=Role.ENGINEER)
    resp = api.post(LOGIN_URL, {"username": "engineer1", "password": PASSWORD}, format="json")
    assert resp.status_code == 200
    assert "access" in resp.data
    assert "refresh" in resp.data


@pytest.mark.django_db
def test_login_rejects_bad_credentials(api):
    make_user("engineer1", role=Role.ENGINEER)
    resp = api.post(LOGIN_URL, {"username": "engineer1", "password": "wrong"}, format="json")
    assert resp.status_code == 401


@pytest.mark.django_db
def test_refresh_returns_new_access(api):
    make_user("engineer1", role=Role.ENGINEER)
    tokens = api.post(
        LOGIN_URL, {"username": "engineer1", "password": PASSWORD}, format="json"
    ).data
    resp = api.post(REFRESH_URL, {"refresh": tokens["refresh"]}, format="json")
    assert resp.status_code == 200
    assert "access" in resp.data


@pytest.mark.django_db
def test_me_requires_auth(api):
    assert api.get(ME_URL).status_code == 401


@pytest.mark.django_db
def test_me_returns_current_user(api):
    make_user("manager1", role=Role.MANAGER, email="m@example.com")
    access = api.post(
        LOGIN_URL, {"username": "manager1", "password": PASSWORD}, format="json"
    ).data["access"]
    resp = auth(api, access).get(ME_URL)
    assert resp.status_code == 200
    assert resp.data["username"] == "manager1"
    assert resp.data["role"] == Role.MANAGER


@pytest.mark.django_db
def test_manager_endpoint_denies_anonymous(api):
    assert api.get(MANAGER_URL).status_code == 401


@pytest.mark.django_db
def test_manager_endpoint_denies_engineer(api):
    make_user("engineer1", role=Role.ENGINEER)
    access = api.post(
        LOGIN_URL, {"username": "engineer1", "password": PASSWORD}, format="json"
    ).data["access"]
    assert auth(api, access).get(MANAGER_URL).status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("role", [Role.MANAGER, Role.ADMIN])
def test_manager_endpoint_allows_manager_and_admin(api, role):
    make_user("u", role=role)
    access = api.post(
        LOGIN_URL, {"username": "u", "password": PASSWORD}, format="json"
    ).data["access"]
    resp = auth(api, access).get(MANAGER_URL)
    assert resp.status_code == 200
    assert resp.data["ok"] is True


@pytest.mark.django_db
def test_superuser_passes_role_gate(api):
    User.objects.create_superuser(username="root", password=PASSWORD)
    access = api.post(
        LOGIN_URL, {"username": "root", "password": PASSWORD}, format="json"
    ).data["access"]
    assert auth(api, access).get(MANAGER_URL).status_code == 200
