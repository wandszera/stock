import uuid
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import ensure_store_access, require_roles
from app.models.audit import AuditEvent
from app.models.inventory import StockMovement
from app.models.user import User
from app.schemas.audit import AuditEventListResponse, AuditEventResponse


router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/events", response_model=AuditEventListResponse)
def list_audit_events(
    store_id: uuid.UUID | None = Query(default=None),
    actor_id: uuid.UUID | None = Query(default=None),
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: uuid.UUID | None = Query(default=None),
    request_id: str | None = Query(default=None),
    created_from: date | None = Query(default=None),
    created_to: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager")),
):
    query = db.query(AuditEvent, User).outerjoin(User, User.id == AuditEvent.actor_id)
    if store_id is not None:
        ensure_store_access(current_user, store_id)
        query = query.filter(AuditEvent.store_id == store_id)
    elif current_user.role != "admin":
        query = query.filter(AuditEvent.store_id == current_user.store_id)
    if actor_id is not None:
        query = query.filter(AuditEvent.actor_id == actor_id)
    if action:
        query = query.filter(AuditEvent.action == action.strip())
    if entity_type:
        query = query.filter(AuditEvent.entity_type == entity_type.strip())
    if entity_id is not None:
        query = query.filter(AuditEvent.entity_id == entity_id)
    if request_id:
        query = query.filter(AuditEvent.request_id == request_id.strip())
    if created_from:
        query = query.filter(
            AuditEvent.created_at >= datetime.combine(created_from, time.min, tzinfo=timezone.utc)
        )
    if created_to:
        query = query.filter(
            AuditEvent.created_at
            < datetime.combine(created_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        )

    total = query.count()
    rows = query.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).offset(offset).limit(limit).all()
    request_ids = {event.request_id for event, _ in rows}
    movements_by_request: dict[str, list[uuid.UUID]] = {key: [] for key in request_ids}
    if request_ids:
        movements = db.query(StockMovement).filter(StockMovement.request_id.in_(request_ids)).all()
        for movement in movements:
            movements_by_request.setdefault(movement.request_id, []).append(movement.id)

    items = [
        AuditEventResponse(
            id=event.id,
            action=event.action,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            store_id=event.store_id,
            actor_id=event.actor_id,
            actor_name=actor.name if actor else None,
            actor_email=actor.email if actor else None,
            request_id=event.request_id,
            metadata=event.event_metadata,
            movement_ids=movements_by_request.get(event.request_id, []),
            created_at=event.created_at,
        )
        for event, actor in rows
    ]
    return {"items": items, "total": total, "limit": limit, "offset": offset}
