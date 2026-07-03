import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class InventoryCountCreate(BaseModel):
    store_id: uuid.UUID
    scope: str = Field(default="cycle", min_length=3, max_length=30)
    reason: str | None = Field(default=None, max_length=255)


class InventoryCountItemCreate(BaseModel):
    variant_id: uuid.UUID
    counted_quantity: int = Field(ge=0)


class InventoryCountItemResponse(BaseModel):
    id: uuid.UUID
    count_id: uuid.UUID
    variant_id: uuid.UUID
    system_quantity: int
    counted_quantity: int
    difference_quantity: int
    counted_at: datetime

    model_config = {"from_attributes": True}


class InventoryCountResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    status: str
    scope: str
    reason: str | None
    created_by: uuid.UUID
    closed_by: uuid.UUID | None
    created_at: datetime
    closed_at: datetime | None
    items: list[InventoryCountItemResponse] = []

    model_config = {"from_attributes": True}
