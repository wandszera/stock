import uuid
from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str


class CategoryResponse(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}