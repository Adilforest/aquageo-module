"""Application gov-flow tests: transitions, permissions, events (PostGIS)."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from accounts.models import Role
from catalog.models import ObjectType, Structure
from common.models import AuditLog
from workflow.models import Application
from workflow.services import TransitionError, decide, submit

User = get_user_model()
LIST = "/api/v1/applications/"


@pytest.fixture
def structure(db):
    ot = ObjectType.objects.create(code="dam", name_ru="Плотина", geometry_kind="point")
    return Structure.objects.create(type=ot, name_ru="Новая плотина", attributes={})


def client_for(role):
    User.objects.create_user(f"u_{role}", password="p", role=role)
    c = APIClient()
    token = APIClient().post(
        "/api/v1/auth/login/", {"username": f"u_{role}", "password": "p"}, format="json"
    ).data["access"]
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return c


def make_app(structure, status=Application.Status.DRAFT):
    return Application.objects.create(
        structure=structure, kind=Application.Kind.CREATE, status=status
    )


# --- service-level transitions ---
@pytest.mark.django_db
def test_submit_valid_and_raises_event(structure):
    user = User.objects.create_user("eng", password="p", role=Role.ENGINEER)
    app = make_app(structure)
    submit(app, user)
    app.refresh_from_db()
    assert app.status == Application.Status.SUBMITTED
    assert app.submitted_at is not None
    assert AuditLog.objects.filter(
        entity_id=str(app.pk), action="application.submitted"
    ).exists()


@pytest.mark.django_db
def test_submit_from_non_draft_invalid(structure):
    app = make_app(structure, status=Application.Status.SUBMITTED)
    with pytest.raises(TransitionError):
        submit(app, None)


@pytest.mark.django_db
def test_decide_approve_and_reject(structure):
    manager = User.objects.create_user("mgr", password="p", role=Role.MANAGER)
    app = make_app(structure, status=Application.Status.SUBMITTED)
    decide(app, manager, approve=True, comment="ок")
    app.refresh_from_db()
    assert app.status == Application.Status.APPROVED
    assert app.reviewer == manager
    assert app.decided_at is not None

    app2 = make_app(structure, status=Application.Status.SUBMITTED)
    decide(app2, manager, approve=False)
    app2.refresh_from_db()
    assert app2.status == Application.Status.REJECTED


@pytest.mark.django_db
def test_decide_from_draft_invalid(structure):
    manager = User.objects.create_user("mgr", password="p", role=Role.MANAGER)
    app = make_app(structure)  # draft
    with pytest.raises(TransitionError):
        decide(app, manager, approve=True)


# --- API + permissions ---
@pytest.mark.django_db
def test_engineer_creates_and_submits(structure):
    client = client_for(Role.ENGINEER)
    created = client.post(
        LIST, {"structure": str(structure.pk), "kind": "create", "comment": "новая"}, format="json"
    )
    assert created.status_code == 201, created.data
    app_id = created.data["id"]
    assert created.data["status"] == "draft"
    resp = client.post(f"{LIST}{app_id}/submit/")
    assert resp.status_code == 200
    assert resp.data["status"] == "submitted"


@pytest.mark.django_db
def test_viewer_cannot_create(structure):
    client = client_for(Role.VIEWER)
    resp = client.post(LIST, {"structure": str(structure.pk), "kind": "create"}, format="json")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_engineer_cannot_decide(structure):
    client = client_for(Role.ENGINEER)
    app = make_app(structure, status=Application.Status.SUBMITTED)
    resp = client.post(f"{LIST}{app.pk}/decide/", {"decision": "approve"}, format="json")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_manager_decides_via_api(structure):
    app = make_app(structure, status=Application.Status.SUBMITTED)
    client = client_for(Role.MANAGER)
    resp = client.post(
        f"{LIST}{app.pk}/decide/", {"decision": "approve", "comment": "ок"}, format="json"
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "approved"


@pytest.mark.django_db
def test_api_invalid_transition_returns_400(structure):
    app = make_app(structure)  # draft
    client = client_for(Role.MANAGER)
    resp = client.post(f"{LIST}{app.pk}/decide/", {"decision": "approve"}, format="json")
    assert resp.status_code == 400  # cannot decide a draft
