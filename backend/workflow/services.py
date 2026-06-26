"""Application state machine with guards + domain events (#25).

draft -> submitted -> approved | rejected. Each transition records a domain
event (audit). Approving a ``kind=create`` application runs the finalization
chain (#26/#27): stub Signature -> generated ApprovalOrder PDF -> publish the
structure. Notifications (#28) come later.
"""
import base64

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from catalog.models import LifecycleStatus
from common.audit import AuditEvent, record

from .models import Application, ApprovalOrder, Signature
from .pdf import render_order_pdf


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


@transaction.atomic
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
    # Gov-flow finalization runs only for approved create applications (#26/#27).
    if approve and application.kind == Application.Kind.CREATE:
        finalize_approval(application, reviewer)
    return application


def finalize_approval(application: Application, reviewer):
    """approve -> Signature(stub) -> ApprovalOrder(PDF) -> Structure.published."""
    signature = create_stub_signature(application, reviewer)
    order = issue_order(application)
    publish_structure(application)
    return signature, order


def create_stub_signature(application: Application, signer) -> Signature:
    """Imitate an ECP signature without NCALayer — always valid, demo subject (#26)."""
    name = str(signer) if getattr(signer, "is_authenticated", False) else "system"
    now = timezone.now()
    cert_subject = f"CN={name}, O=AquaGeo (DEMO), OU=Gov-flow, C=KZ"
    cms_blob = base64.b64encode(
        f"DEMO-CMS::{application.pk}::{name}::{now.isoformat()}".encode()
    ).decode()
    signature = Signature.objects.create(
        application=application,
        signer=name,
        signed_at=now,
        cert_subject=cert_subject,
        cms_blob=cms_blob,
        valid=True,
    )
    record(AuditEvent(
        actor=name, action="signature.created",
        entity_type="signature", entity_id=str(signature.pk),
        payload={"application": str(application.pk), "valid": True},
    ))
    return signature


def next_order_number() -> str:
    year = timezone.now().year
    seq = ApprovalOrder.objects.filter(number__startswith=f"ORD-{year}-").count() + 1
    return f"ORD-{year}-{seq:04d}"


def issue_order(application: Application) -> ApprovalOrder:
    """Generate the approval order PDF and persist it as an ApprovalOrder (#27)."""
    issued_at = timezone.now()
    number = next_order_number()
    pdf_bytes = render_order_pdf(application, number, issued_at)
    order = ApprovalOrder(application=application, number=number, issued_at=issued_at)
    order.file.save(f"order-{number}.pdf", ContentFile(pdf_bytes), save=True)
    record(AuditEvent(
        actor="system", action="order.generated",
        entity_type="order", entity_id=str(order.pk),
        payload={"application": str(application.pk), "number": number},
    ))
    return order


def publish_structure(application: Application) -> None:
    """Move the structure draft -> published on approval (#27)."""
    structure = application.structure
    structure.status = LifecycleStatus.PUBLISHED
    structure.save(update_fields=["status", "updated_at"])
    record(AuditEvent(
        actor="system", action="structure.published",
        entity_type="structure", entity_id=str(structure.pk),
        payload={"application": str(application.pk)},
    ))
