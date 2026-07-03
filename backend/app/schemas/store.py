import uuid

from pydantic import BaseModel


class StoreCreate(BaseModel):
    name: str
    timezone: str = "America/Sao_Paulo"
    is_active: bool = True


class StoreUpdate(BaseModel):
    name: str | None = None
    timezone: str | None = None
    is_active: bool | None = None


class StoreResponse(BaseModel):
    id: uuid.UUID
    name: str
    timezone: str
    is_active: bool

    model_config = {"from_attributes": True}
