import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class SupplierDeliveryCreate(BaseModel):
    store_id: uuid.UUID
    supplier_reference: str = Field(min_length=1, max_length=160)
    document_reference: str | None = Field(default=None, max_length=120)
    ordered_at: date
    expected_at: date
    delivered_at: date
    ordered_quantity: int = Field(gt=0)
    received_quantity: int = Field(ge=0)
    defective_quantity: int = Field(default=0, ge=0)
    purchase_cost: Decimal = Field(ge=0, max_digits=14, decimal_places=2)

    @model_validator(mode="after")
    def validate_delivery(self):
        self.supplier_reference = self.supplier_reference.strip()
        if self.expected_at < self.ordered_at or self.delivered_at < self.ordered_at:
            raise ValueError("As datas de entrega nao podem anteceder o pedido.")
        if self.defective_quantity > self.received_quantity:
            raise ValueError("A quantidade defeituosa nao pode superar a recebida.")
        return self


class SupplierDeliveryResponse(SupplierDeliveryCreate):
    id: uuid.UUID
    created_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class SupplierRiskRun(BaseModel):
    store_id: uuid.UUID
    supplier_reference: str | None = Field(default=None, min_length=1, max_length=160)


class SupplierRiskResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    supplier_reference: str
    score: Decimal
    risk_level: str
    components: dict
    explanation: str
    delivery_count: int
    created_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class SupplierRiskListResponse(BaseModel):
    items: list[SupplierRiskResponse]
    total: int
