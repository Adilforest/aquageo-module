"""Application state machine with guards + domain events (#25).

draft -> submitted -> approved | rejected. Each transition records a domain
event (audit). Notifications (#28) and signature/PDF/publish (#26/#27) come later.
"""
from django.utils import timezone

from common.audit import AuditEvent, record

from .models import Application


class TransitionError(Exception):
    """Raised on an invalid status transition."""


def submit(application: Application, user) -> Application:
    if application.status != Application.Status.DRAFT:
        raise TransitionError(f"submit недопустим из статуса {application.status}")
    application.status = Application.Status.SUBMITTED
    application.submitted_at = timezone.now()
    if application.submitted_by is None and getattr(user, "is_authenticated", False):
        application.submitted_by = user
    application.save(update_fields=["status", "submitted_at", "submitted_by", "updated_at"])
    record(AuditEvent(
        actor=str(user), action="application.submitted",
        entity_type="application", entity_id=str(application.pk),
        payload={"kind": application.kind, "structure": str(application.structure_id)},
    ))
    return application


def decide(application: Application, reviewer, *, approve: bool, comment: str = "") -> Application:
    if application.status != Application.Status.SUBMITTED:
        raise TransitionError(f"решение недопустимо из статуса {application.status}")
    application.status = (
        Application.Status.APPROVED if approve else Application.Status.REJECTED
    )
    application.reviewer = reviewer if getattr(reviewer, "is_authenticated", False) else None
    application.decided_at = timezone.now()
    if comment:
        application.comment = comment
    application.save(
        update_fields=["status", "reviewer", "decided_at", "comment", "updated_at"]
    )
    record(AuditEvent(
        actor=str(reviewer),
        action=f"application.{application.status}",
        entity_type="application", entity_id=str(application.pk),
        payload={"comment": comment},
    ))
    return application
