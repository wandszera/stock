import uuid
from decimal import Decimal
from pydantic import BaseModel


class ProductCreate(BaseModel):
    name: str
    brand: str | None = None
    description: str | None = None
    category_id: uuid.UUID | None = None


class ProductResponse(BaseModel):
    id: uuid.UUID
    name: str
    brand: str | None
    description: str | None
    is_active: bool
    category_id: uuid.UUID | None

    model_config = {"from_attributes": True}


class ProductUpdate(BaseModel):
    name: str | None = None
    brand: str | None = None
    description: str | None = None
    category_id: uuid.UUID | None = None
    is_active: bool | None = None


class VariantCreate(BaseModel):
    product_id: uuid.UUID
    sku: str
    barcode: str | None = None
    cost_price: Decimal
    sale_price: Decimal


class VariantResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    sku: str
    barcode: str | None
    cost_price: Decimal
    sale_price: Decimal

    model_config = {"from_attributes": True}


class VariantUpdate(BaseModel):
    product_id: uuid.UUID | None = None
    sku: str | None = None
    barcode: str | None = None
    cost_price: Decimal | None = None
    sale_price: Decimal | None = None
