import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class InventoryBalanceResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    variant_id: uuid.UUID
    on_hand_qty: int
    reserved_qty: int
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class StockMovementResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    variant_id: uuid.UUID
    movement_type: str
    quantity_delta: int
    reference_type: str
    reference_id: uuid.UUID | None
    supplier_reference: str | None
    document_reference: str | None
    reason: str | None
    created_by: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class StockMovementListResponse(BaseModel):
    items: list[StockMovementResponse]
    total: int
    limit: int
    offset: int


class ReceiptReferenceSummary(BaseModel):
    supplier_reference: str | None
    document_reference: str | None
    reason: str | None
    store_id: uuid.UUID
    created_at: datetime
    item_count: int
    total_quantity: int


class ReceiptSummary(BaseModel):
    receipt_id: str
    status: str
    requires_approval: bool
    approved_by: uuid.UUID | None
    supplier_reference: str | None
    document_reference: str | None
    reason: str | None
    notes: str | None
    store_id: uuid.UUID
    created_at: datetime
    item_count: int
    total_quantity: int


class ReceiptListResponse(BaseModel):
    items: list[ReceiptSummary]
    total: int
    limit: int
    offset: int


class ReceiptMovementItem(BaseModel):
    receipt_item_id: uuid.UUID
    movement_id: uuid.UUID | None = None
    variant_id: uuid.UUID
    quantity: int
    created_at: datetime


class ReceiptDetail(BaseModel):
    receipt_id: str
    status: str
    requires_approval: bool
    approved_by: uuid.UUID | None
    supplier_reference: str | None
    document_reference: str | None
    reason: str | None
    notes: str | None
    store_id: uuid.UUID
    created_at: datetime
    item_count: int
    total_quantity: int
    items: list[ReceiptMovementItem]
    audit: list["ReceiptAuditEntry"]


class ReceiptAuditEntry(BaseModel):
    action: str
    details: str | None
    created_by: uuid.UUID | None
    created_at: datetime


class ReceiptDocumentReportEntry(BaseModel):
    status: str
    supplier_reference: str | None
    receipts: int
    total_quantity: int
    requires_approval: bool
    pending_approval_receipts: int
    approved_receipts: int
    supplier_target_hours: int | None = None


class ReceiptDocumentReport(BaseModel):
    items: list[ReceiptDocumentReportEntry]
    total: int
    limit: int
    offset: int
    created_from: datetime | None
    created_to: datetime | None


class SupplierRiskTargetUpsert(BaseModel):
    store_id: uuid.UUID
    supplier_reference: str = Field(min_length=1, max_length=160)
    target_hours: int = Field(ge=1, le=720)


class SupplierRiskTargetResponse(BaseModel):
    store_id: uuid.UUID
    supplier_reference: str
    target_hours: int
    updated_by: uuid.UUID | None
    updated_at: datetime | None


class SupplierRiskHistoryEntry(BaseModel):
    supplier_reference: str
    snapshot_date: datetime
    target_hours: int
    open_critical_count: int
    resolved_estimate_count: int


class SupplierRiskHistoryResponse(BaseModel):
    items: list[SupplierRiskHistoryEntry]


class ReceiptStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=30)


class InventoryReceiptCreate(BaseModel):
    store_id: uuid.UUID
    supplier_reference: str | None = Field(default=None, max_length=160)
    document_reference: str | None = Field(default=None, max_length=120)
    reason: str | None = None
    notes: str | None = Field(default=None, max_length=500)
    created_by: uuid.UUID | None = None
    items: list["InventoryEntryItemCreate"]


class InventoryReceiptDraftUpdate(BaseModel):
    supplier_reference: str | None = Field(default=None, max_length=160)
    document_reference: str | None = Field(default=None, max_length=120)
    reason: str | None = None
    notes: str | None = Field(default=None, max_length=500)
    items: list["InventoryEntryItemCreate"]


class InventoryEntryCreate(BaseModel):
    store_id: uuid.UUID
    variant_id: uuid.UUID
    quantity: int = Field(gt=0)
    supplier_reference: str | None = Field(default=None, max_length=160)
    document_reference: str | None = Field(default=None, max_length=120)
    reason: str | None = None
    created_by: uuid.UUID | None = None


class InventoryEntryItemCreate(BaseModel):
    variant_id: uuid.UUID
    quantity: int = Field(gt=0)


class InventoryBatchEntryCreate(BaseModel):
    store_id: uuid.UUID
    supplier_reference: str | None = Field(default=None, max_length=160)
    document_reference: str | None = Field(default=None, max_length=120)
    reason: str | None = None
    created_by: uuid.UUID | None = None
    items: list[InventoryEntryItemCreate]


class InventoryBatchEntryResponse(BaseModel):
    store_id: uuid.UUID
    balances: list[InventoryBalanceResponse]


class InventoryAdjustmentCreate(BaseModel):
    store_id: uuid.UUID
    variant_id: uuid.UUID
    new_quantity: int = Field(ge=0)
    reason: str
    created_by: uuid.UUID | None = None


class InventoryTransferCreate(BaseModel):
    source_store_id: uuid.UUID
    destination_store_id: uuid.UUID
    variant_id: uuid.UUID
    quantity: int = Field(gt=0)
    reason: str | None = None
    created_by: uuid.UUID | None = None
