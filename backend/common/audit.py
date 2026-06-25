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
    """Record an audit event.

    Placeholder implementation logs at DEBUG. Issue #29 replaces this with a
    persisted ``AuditLog`` row.
    """
    logger.debug(
        "audit: actor=%s action=%s entity=%s/%s",
        event.actor,
        event.action,
        event.entity_type,
        event.entity_id,
    )
