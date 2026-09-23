"""Persistence helpers for the unified operational audit trail."""

import uuid

from sqlalchemy.orm import Session

from app.core.observability import request_id_context
from app.models.audit import AuditEvent


def record_audit_event(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    store_id: uuid.UUID | None = None,
    metadata: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        store_id=store_id,
        actor_id=actor_id,
        request_id=request_id_context.get(),
        event_metadata=metadata,
    )
    db.add(event)
    return event
