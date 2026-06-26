"""Turn existing domain events into notifications (issue #28).

Every domain event in this codebase is recorded as a ``common.models.AuditLog``
row via ``common.audit.record`` (see workflow/assessment services). We subscribe
to that single stream with a ``post_save`` receiver instead of inventing new
trigger points: when an AuditLog row appears with a known ``action`` we fan it
out to the right recipients. The handler is fully defensive — any failure is
logged and swallowed so it can never break the originating transaction (e.g. an
``application.decide`` inside ``@transaction.atomic``).

Mapping (only events that already fire):
- application.submitted        -> managers + admins
- application.approved/rejected -> the application author (submitted_by)
- risk.alert                   -> managers + admins (responsible/admin)
"""
from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from common.models import AuditLog

from .models import Notification

logger = logging.getLogger("aquageo.notifications")

_HANDLED_ACTIONS = {
    "application.submitted",
    "application.approved",
    "application.rejected",
    "risk.alert",
}


def _managers_and_admins():
    from accounts.models import Role, User

    return User.objects.filter(
        role__in=[Role.MANAGER, Role.ADMIN], is_active=True
    )


def _structure_name(structure_id: str) -> str:
    from catalog.models import Structure

    structure = Structure.objects.filter(pk=structure_id).first()
    return (structure.name_ru if structure else None) or str(structure_id)


def _on_application_submitted(log: AuditLog) -> None:
    from workflow.models import Application

    app = (
        Application.objects.select_related("structure")
        .filter(pk=log.entity_id)
        .first()
    )
    if app is None:
        return
    name = app.structure.name_ru or str(app.structure_id)
    message = f"Новая заявка на согласование: {app.get_kind_display().lower()} «{name}»"
    Notification.objects.bulk_create(
        [
            Notification(
                recipient=user,
                kind=Notification.Kind.APPLICATION_SUBMITTED,
                message=message,
                related_entity_type="application",
                related_entity_id=str(app.pk),
            )
            for user in _managers_and_admins()
        ]
    )


def _on_application_decided(log: AuditLog, *, approved: bool) -> None:
    from workflow.models import Application

    app = (
        Application.objects.select_related("structure", "submitted_by")
        .filter(pk=log.entity_id)
        .first()
    )
    if app is None or app.submitted_by is None:
        return
    name = app.structure.name_ru or str(app.structure_id)
    if approved:
        kind = Notification.Kind.APPLICATION_APPROVED
        message = f"Ваша заявка «{name}» согласована"
    else:
        kind = Notification.Kind.APPLICATION_REJECTED
        message = f"Ваша заявка «{name}» отклонена"
        comment = (log.payload or {}).get("comment")
        if comment:
            message += f". Комментарий: {comment}"
    Notification.objects.create(
        recipient=app.submitted_by,
        kind=kind,
        message=message,
        related_entity_type="application",
        related_entity_id=str(app.pk),
    )


def _on_risk_alert(log: AuditLog) -> None:
    name = _structure_name(log.entity_id)
    level = (log.payload or {}).get("max_level", "")
    suffix = f" (уровень: {level})" if level else ""
    message = f"Риск-оповещение по объекту «{name}»{suffix}"
    Notification.objects.bulk_create(
        [
            Notification(
                recipient=user,
                kind=Notification.Kind.RISK_ALERT,
                message=message,
                related_entity_type="structure",
                related_entity_id=str(log.entity_id),
            )
            for user in _managers_and_admins()
        ]
    )


@receiver(post_save, sender=AuditLog, dispatch_uid="notifications.on_audit_log")
def on_audit_log(sender, instance: AuditLog, created: bool, **kwargs) -> None:
    if not created or instance.action not in _HANDLED_ACTIONS:
        return
    try:
        if instance.action == "application.submitted":
            _on_application_submitted(instance)
        elif instance.action == "application.approved":
            _on_application_decided(instance, approved=True)
        elif instance.action == "application.rejected":
            _on_application_decided(instance, approved=False)
        elif instance.action == "risk.alert":
            _on_risk_alert(instance)
    except Exception:  # never break the originating flow
        logger.exception("notifications: failed to handle %s", instance.action)
