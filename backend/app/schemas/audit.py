import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AuditEventResponse(BaseModel):
    id: uuid.UUID
    action: str
    entity_type: str
    entity_id: uuid.UUID
    store_id: uuid.UUID | None
    actor_id: uuid.UUID | None
    actor_name: str | None = None
    actor_email: str | None = None
    request_id: str
    metadata: dict | None = None
    movement_ids: list[uuid.UUID] = Field(default_factory=list)
    created_at: datetime


class AuditEventListResponse(BaseModel):
    items: list[AuditEventResponse]
    total: int
    limit: int
    offset: int
