"""Inventory domain helpers.

This module keeps persistence and authorization helpers out of the HTTP route
module.  The route handlers remain responsible for request/response concerns,
while the shared stock and receipt rules live here.
"""

import uuid
from datetime import date, datetime, time, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import ensure_store_access
from app.core.observability import request_id_context
from app.models.inventory import (
    InventoryBalance,
    InventoryReceipt,
    InventoryReceiptAuditLog,
    InventoryReceiptItem,
    InventorySupplierRiskSnapshot,
    InventorySupplierRiskTarget,
    StockMovement,
)
from app.models.product import ProductVariant
from app.models.user import User


VALID_RECEIPT_STATUSES = {"draft", "posted", "checked", "canceled"}
ALLOWED_RECEIPT_STATUS_TRANSITIONS = {
    "draft": set(),
    "posted": {"posted", "checked"},
    "checked": {"checked", "posted"},
    "canceled": set(),
}
RECEIPT_APPROVAL_THRESHOLD = 20


class StockConflictError(Exception):
    """Raised when a stock mutation cannot preserve inventory invariants."""


def lock_inventory_balance(
    db: Session,
    store_id: uuid.UUID,
    variant_id: uuid.UUID,
    *,
    create_if_missing: bool = False,
) -> InventoryBalance:
    """Load a balance with a row lock, optionally creating an empty balance.

    PostgreSQL holds the lock until the surrounding transaction commits or
    rolls back. SQLite ignores ``FOR UPDATE``, but the same code path and
    invariants remain useful in local development and tests.
    """
    balance = (
        db.query(InventoryBalance)
        .filter(
            InventoryBalance.store_id == store_id,
            InventoryBalance.variant_id == variant_id,
        )
        .with_for_update()
        .first()
    )
    if balance is not None:
        return balance
    if not create_if_missing:
        raise StockConflictError("Saldo de estoque nao encontrado.")

    # A missing balance row cannot itself be locked. Locking the parent variant
    # serializes first-balance creation, then a second lookup observes a row
    # that a concurrent transaction may have inserted while we waited.
    variant = (
        db.query(ProductVariant)
        .filter(ProductVariant.id == variant_id)
        .with_for_update()
        .first()
    )
    if variant is None:
        raise StockConflictError("Variante de produto nao encontrada.")
    balance = (
        db.query(InventoryBalance)
        .filter(
            InventoryBalance.store_id == store_id,
            InventoryBalance.variant_id == variant_id,
        )
        .with_for_update()
        .first()
    )
    if balance is not None:
        return balance

    balance = InventoryBalance(
        store_id=store_id,
        variant_id=variant_id,
        on_hand_qty=0,
        reserved_qty=0,
    )
    db.add(balance)
    db.flush()
    return balance


def lock_inventory_balances(
    db: Session,
    keys: list[tuple[uuid.UUID, uuid.UUID]],
    *,
    create_if_missing: bool = False,
) -> dict[tuple[uuid.UUID, uuid.UUID], InventoryBalance]:
    """Lock several balances in stable order to reduce deadlock risk."""
    locked: dict[tuple[uuid.UUID, uuid.UUID], InventoryBalance] = {}
    for store_id, variant_id in sorted(set(keys), key=lambda item: (str(item[0]), str(item[1]))):
        locked[(store_id, variant_id)] = lock_inventory_balance(
            db,
            store_id,
            variant_id,
            create_if_missing=create_if_missing,
        )
    return locked


def change_stock(
    db: Session,
    *,
    store_id: uuid.UUID,
    variant_id: uuid.UUID,
    quantity_delta: int,
    movement_type: str,
    reference_type: str,
    created_by: uuid.UUID | None,
    create_if_missing: bool = False,
    receipt_group_id: uuid.UUID | None = None,
    reference_id: uuid.UUID | None = None,
    supplier_reference: str | None = None,
    document_reference: str | None = None,
    reason: str | None = None,
) -> InventoryBalance:
    """Atomically mutate a locked balance and append its ledger movement."""
    balance = lock_inventory_balance(
        db,
        store_id,
        variant_id,
        create_if_missing=create_if_missing,
    )
    next_quantity = balance.on_hand_qty + quantity_delta
    if next_quantity < 0:
        raise StockConflictError(f"Estoque insuficiente para {variant_id}.")

    balance.on_hand_qty = next_quantity
    db.add(
        StockMovement(
            store_id=store_id,
            variant_id=variant_id,
            movement_type=movement_type,
            quantity_delta=quantity_delta,
            reference_type=reference_type,
            receipt_group_id=receipt_group_id,
            reference_id=reference_id,
            supplier_reference=supplier_reference,
            document_reference=document_reference,
            reason=reason,
            created_by=created_by,
            request_id=request_id_context.get(),
        )
    )
    return balance


def set_stock_quantity(
    db: Session,
    *,
    store_id: uuid.UUID,
    variant_id: uuid.UUID,
    quantity: int,
    reference_type: str,
    created_by: uuid.UUID | None,
    reference_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> tuple[InventoryBalance, int]:
    """Set an absolute quantity while holding the balance row lock."""
    balance = lock_inventory_balance(db, store_id, variant_id, create_if_missing=True)
    delta = quantity - balance.on_hand_qty
    if delta:
        balance.on_hand_qty = quantity
        db.add(
            StockMovement(
                store_id=store_id,
                variant_id=variant_id,
                movement_type="adjustment",
                quantity_delta=delta,
                reference_type=reference_type,
                reference_id=reference_id,
                reason=reason,
                created_by=created_by,
                request_id=request_id_context.get(),
            )
        )
    return balance, delta


def build_receipt_id(movement: StockMovement) -> str:
    if movement.receipt_group_id:
        return str(movement.receipt_group_id)
    supplier = movement.supplier_reference or "-"
    document = movement.document_reference or "-"
    reason = movement.reason or "-"
    return f"{movement.store_id}|{supplier}|{document}|{reason}"


def ensure_receipt_header(
    db: Session,
    *,
    receipt_id: uuid.UUID,
    store_id: uuid.UUID,
    supplier_reference: str | None,
    document_reference: str | None,
    reason: str | None,
    created_by: uuid.UUID | None,
):
    receipt = db.query(InventoryReceipt).filter(InventoryReceipt.id == receipt_id).first()
    if receipt:
        return receipt
    receipt = InventoryReceipt(
        id=receipt_id,
        store_id=store_id,
        status="draft",
        supplier_reference=supplier_reference,
        document_reference=document_reference,
        reason=reason,
        created_by=created_by,
    )
    db.add(receipt)
    db.flush()
    return receipt


def get_receipt_items(db: Session, receipt_id: uuid.UUID):
    return (
        db.query(InventoryReceiptItem)
        .filter(InventoryReceiptItem.receipt_id == receipt_id)
        .order_by(InventoryReceiptItem.created_at.desc(), InventoryReceiptItem.id.desc())
        .all()
    )


def add_receipt_audit_log(
    db: Session,
    *,
    receipt_id: uuid.UUID,
    action: str,
    created_by: uuid.UUID | None,
    details: str | None = None,
):
    db.add(
        InventoryReceiptAuditLog(
            receipt_id=receipt_id,
            action=action,
            details=details,
            created_by=created_by,
        )
    )


def compute_requires_receipt_approval(items: list[InventoryReceiptItem] | list) -> bool:
    return sum(int(item.quantity) for item in items) >= RECEIPT_APPROVAL_THRESHOLD


def get_supplier_target_map(db: Session, store_id: uuid.UUID | None) -> dict[str, int]:
    if store_id is None:
        return {}
    targets = (
        db.query(InventorySupplierRiskTarget)
        .filter(InventorySupplierRiskTarget.store_id == store_id)
        .all()
    )
    return {item.supplier_reference: item.target_hours for item in targets}


def upsert_supplier_risk_snapshots(
    db: Session,
    *,
    store_id: uuid.UUID | None,
    receipts: list[InventoryReceipt],
    supplier_target_map: dict[str, int],
):
    if store_id is None:
        return
    today = datetime.now(timezone.utc).date()
    grouped: dict[str, dict[str, int]] = {}
    for receipt in receipts:
        supplier = receipt.supplier_reference or "Nao informado"
        if supplier not in grouped:
            grouped[supplier] = {"open_critical_count": 0, "resolved_estimate_count": 0}
        if receipt.status == "draft" and receipt.requires_approval and receipt.approved_by is None:
            grouped[supplier]["open_critical_count"] += 1
        else:
            grouped[supplier]["resolved_estimate_count"] += 1

    for supplier, values in grouped.items():
        snapshot = (
            db.query(InventorySupplierRiskSnapshot)
            .filter(
                InventorySupplierRiskSnapshot.store_id == store_id,
                InventorySupplierRiskSnapshot.supplier_reference == supplier,
                InventorySupplierRiskSnapshot.snapshot_date == today,
            )
            .first()
        )
        if not snapshot:
            snapshot = InventorySupplierRiskSnapshot(
                store_id=store_id,
                supplier_reference=supplier,
                snapshot_date=today,
            )
            db.add(snapshot)
        snapshot.target_hours = supplier_target_map.get(supplier, 48)
        snapshot.open_critical_count = values["open_critical_count"]
        snapshot.resolved_estimate_count = values["resolved_estimate_count"]


def ensure_receipt_draft_control(current_user: User, receipt: InventoryReceipt) -> None:
    ensure_store_access(current_user, receipt.store_id)
    if current_user.role in {"admin", "manager"}:
        return
    if current_user.role == "operator" and receipt.created_by == current_user.id:
        return
    raise HTTPException(status_code=403, detail="Usuario sem permissao para alterar este rascunho.")


def apply_movement_filters(
    query,
    *,
    current_user: User,
    store_id: uuid.UUID | None,
    variant_id: uuid.UUID | None,
    movement_type: str | None,
    reference_type: str | None,
    supplier_reference: str | None,
    document_reference: str | None,
    created_from: date | None,
    created_to: date | None,
):
    if store_id is not None:
        ensure_store_access(current_user, store_id)
        query = query.filter(StockMovement.store_id == store_id)
    elif current_user.role != "admin":
        query = query.filter(StockMovement.store_id == current_user.store_id)

    if variant_id is not None:
        query = query.filter(StockMovement.variant_id == variant_id)
    if movement_type is not None:
        query = query.filter(StockMovement.movement_type == movement_type)
    if reference_type is not None:
        query = query.filter(StockMovement.reference_type == reference_type)
    if supplier_reference is not None:
        query = query.filter(StockMovement.supplier_reference.ilike(f"%{supplier_reference.strip()}%"))
    if document_reference is not None:
        query = query.filter(StockMovement.document_reference.ilike(f"%{document_reference.strip()}%"))
    if created_from is not None:
        query = query.filter(
            StockMovement.created_at >= datetime.combine(created_from, time.min, tzinfo=timezone.utc)
        )
    if created_to is not None:
        query = query.filter(
            StockMovement.created_at
            < datetime.combine(created_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        )
    return query
