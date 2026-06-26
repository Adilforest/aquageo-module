"""Audit scaffolding.

A lightweight hook for recording actor/action/entity. The persistent
``AuditLog`` model and signal wiring land in issue #29; for now this is a
no-op placeholder so call sites can be introduced early without churn.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("aquageo.audit")


@dataclass(frozen=True)
class AuditEvent:
    actor: str | None
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    payload: dict[str, Any] | None = None


def record(event: AuditEvent) -> None:
    """Persist an audit event as an ``AuditLog`` row (and log at DEBUG)."""
    from .models import AuditLog

    logger.debug(
        "audit: actor=%s action=%s entity=%s/%s",
        event.actor,
        event.action,
        event.entity_type,
        event.entity_id,
    )
    AuditLog.objects.create(
        actor=event.actor or "",
        action=event.action,
        entity_type=event.entity_type or "",
        entity_id=event.entity_id or "",
        payload=event.payload or {},
    )
