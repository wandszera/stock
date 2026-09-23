import csv
import io
import uuid
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import ensure_store_access, get_current_user, require_roles
from app.models.inventory import (
    InventoryBalance,
    InventoryReceiptAuditLog,
    InventoryReceipt,
    InventoryReceiptItem,
    InventorySupplierRiskSnapshot,
    InventorySupplierRiskTarget,
    StockMovement,
)
from app.models.user import User
from app.services.inventory import (
    ALLOWED_RECEIPT_STATUS_TRANSITIONS,
    StockConflictError,
    VALID_RECEIPT_STATUSES,
    add_receipt_audit_log,
    apply_movement_filters,
    build_receipt_id,
    change_stock,
    compute_requires_receipt_approval,
    ensure_receipt_draft_control,
    ensure_receipt_header,
    get_receipt_items,
    get_supplier_target_map,
    lock_inventory_balances,
    set_stock_quantity,
    upsert_supplier_risk_snapshots,
)
from app.services.audit import record_audit_event
from app.schemas.inventory import (
    InventoryAdjustmentCreate,
    InventoryBatchEntryCreate,
    InventoryBatchEntryResponse,
    InventoryBalanceResponse,
    InventoryEntryCreate,
    InventoryReceiptCreate,
    InventoryReceiptDraftUpdate,
    InventoryTransferCreate,
    ReceiptAuditEntry,
    ReceiptDetail,
    ReceiptListResponse,
    ReceiptDocumentReport,
    ReceiptDocumentReportEntry,
    ReceiptMovementItem,
    ReceiptReferenceSummary,
    ReceiptStatusUpdate,
    ReceiptSummary,
    SupplierRiskHistoryEntry,
    SupplierRiskHistoryResponse,
    SupplierRiskTargetResponse,
    SupplierRiskTargetUpsert,
    StockMovementListResponse,
    StockMovementResponse,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])


def batch_receipt_matches_idempotent_request(
    receipt: InventoryReceipt,
    items: list[InventoryReceiptItem],
    payload: InventoryBatchEntryCreate,
) -> bool:
    persisted_items = sorted((str(item.variant_id), item.quantity) for item in items)
    requested_items = sorted((str(item.variant_id), item.quantity) for item in payload.items)
    return (
        receipt.supplier_reference == payload.supplier_reference
        and receipt.document_reference == payload.document_reference
        and receipt.reason == payload.reason
        and persisted_items == requested_items
    )


def ensure_matching_batch_receipt(
    receipt: InventoryReceipt,
    items: list[InventoryReceiptItem],
    payload: InventoryBatchEntryCreate,
) -> None:
    if not batch_receipt_matches_idempotent_request(receipt, items, payload):
        raise HTTPException(
            status_code=409,
            detail="Idempotency-Key ja foi usado com um recebimento diferente.",
        )


@router.get("/balances", response_model=list[InventoryBalanceResponse])
def list_balances(
    store_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(InventoryBalance)
    if store_id is not None:
        ensure_store_access(current_user, store_id)
        query = query.filter(InventoryBalance.store_id == store_id)
    elif current_user.role != "admin":
        query = query.filter(InventoryBalance.store_id == current_user.store_id)
    return query.all()


@router.get("/movements", response_model=StockMovementListResponse)
def list_movements(
    store_id: uuid.UUID | None = Query(default=None),
    variant_id: uuid.UUID | None = Query(default=None),
    movement_type: str | None = Query(default=None),
    reference_type: str | None = Query(default=None),
    supplier_reference: str | None = Query(default=None),
    document_reference: str | None = Query(default=None),
    created_from: date | None = Query(default=None),
    created_to: date | None = Query(default=None),
    limit: int = Query(default=12, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = apply_movement_filters(
        db.query(StockMovement),
        current_user=current_user,
        store_id=store_id,
        variant_id=variant_id,
        movement_type=movement_type,
        reference_type=reference_type,
        supplier_reference=supplier_reference,
        document_reference=document_reference,
        created_from=created_from,
        created_to=created_to,
    )

    total = query.count()
    items = query.order_by(StockMovement.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/movements/export")
def export_movements_csv(
    store_id: uuid.UUID | None = Query(default=None),
    variant_id: uuid.UUID | None = Query(default=None),
    movement_type: str | None = Query(default=None),
    reference_type: str | None = Query(default=None),
    supplier_reference: str | None = Query(default=None),
    document_reference: str | None = Query(default=None),
    created_from: date | None = Query(default=None),
    created_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = apply_movement_filters(
        db.query(StockMovement),
        current_user=current_user,
        store_id=store_id,
        variant_id=variant_id,
        movement_type=movement_type,
        reference_type=reference_type,
        supplier_reference=supplier_reference,
        document_reference=document_reference,
        created_from=created_from,
        created_to=created_to,
    )

    items = query.order_by(StockMovement.created_at.desc()).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "receipt_group_id",
            "movement_id",
            "created_at",
            "store_id",
            "variant_id",
            "movement_type",
            "quantity_delta",
            "reference_type",
            "reference_id",
            "supplier_reference",
            "document_reference",
            "reason",
            "created_by",
        ]
    )
    for item in items:
        writer.writerow(
            [
                item.receipt_group_id or "",
                item.id,
                item.created_at.isoformat(),
                item.store_id,
                item.variant_id,
                item.movement_type,
                item.quantity_delta,
                item.reference_type,
                item.reference_id or "",
                item.supplier_reference or "",
                item.document_reference or "",
                item.reason or "",
                item.created_by or "",
            ]
        )

    filename_date = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="movements-{filename_date}.csv"'},
    )


@router.get("/receipt-references", response_model=list[ReceiptReferenceSummary])
def list_recent_receipt_references(
    store_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=6, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = apply_movement_filters(
        db.query(StockMovement),
        current_user=current_user,
        store_id=store_id,
        variant_id=None,
        movement_type="entry",
        reference_type=None,
        supplier_reference=None,
        document_reference=None,
        created_from=None,
        created_to=None,
    ).filter(
        (StockMovement.supplier_reference.isnot(None)) | (StockMovement.document_reference.isnot(None))
    )

    movements = query.order_by(StockMovement.created_at.desc()).all()
    grouped: dict[tuple[str, str, str, uuid.UUID], ReceiptReferenceSummary] = {}
    for movement in movements:
        key = (
            movement.supplier_reference or "",
            movement.document_reference or "",
            movement.reason or "",
            movement.store_id,
        )
        if key not in grouped:
            if len(grouped) >= limit:
                continue
            grouped[key] = ReceiptReferenceSummary(
                supplier_reference=movement.supplier_reference,
                document_reference=movement.document_reference,
                reason=movement.reason,
                store_id=movement.store_id,
                created_at=movement.created_at,
                item_count=0,
                total_quantity=0,
            )
        grouped[key].item_count += 1
        grouped[key].total_quantity += movement.quantity_delta

    return sorted(
        grouped.values(),
        key=lambda item: (
            item.created_at,
            item.document_reference or "",
            item.supplier_reference or "",
        ),
        reverse=True,
    )


@router.get("/receipts", response_model=ReceiptListResponse)
def list_receipts(
    store_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    requires_approval: bool | None = Query(default=None),
    q: str | None = Query(default=None),
    supplier_reference: str | None = Query(default=None),
    document_reference: str | None = Query(default=None),
    created_from: date | None = Query(default=None),
    created_to: date | None = Query(default=None),
    limit: int = Query(default=12, ge=1, le=40),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    receipt_query = db.query(InventoryReceipt)
    if store_id is not None:
        ensure_store_access(current_user, store_id)
        receipt_query = receipt_query.filter(InventoryReceipt.store_id == store_id)
    elif current_user.role != "admin":
        receipt_query = receipt_query.filter(InventoryReceipt.store_id == current_user.store_id)
    if status is not None:
        receipt_query = receipt_query.filter(InventoryReceipt.status == status)
    if requires_approval is not None:
        receipt_query = receipt_query.filter(InventoryReceipt.requires_approval == requires_approval)
    if q is not None:
        search = f"%{q.strip()}%"
        receipt_query = receipt_query.filter(
            or_(
                InventoryReceipt.supplier_reference.ilike(search),
                InventoryReceipt.document_reference.ilike(search),
            )
        )
    if supplier_reference is not None:
        receipt_query = receipt_query.filter(InventoryReceipt.supplier_reference.ilike(f"%{supplier_reference.strip()}%"))
    if document_reference is not None:
        receipt_query = receipt_query.filter(InventoryReceipt.document_reference.ilike(f"%{document_reference.strip()}%"))
    if created_from is not None:
        receipt_query = receipt_query.filter(
            InventoryReceipt.received_at >= datetime.combine(created_from, time.min, tzinfo=timezone.utc)
        )
    if created_to is not None:
        receipt_query = receipt_query.filter(
            InventoryReceipt.received_at < datetime.combine(created_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        )

    total = receipt_query.count()
    receipts = (
        receipt_query
        .order_by(InventoryReceipt.received_at.desc(), InventoryReceipt.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    items: list[ReceiptSummary] = []
    for receipt in receipts:
        receipt_items = get_receipt_items(db, receipt.id)
        items.append(
            ReceiptSummary(
                receipt_id=str(receipt.id),
                status=receipt.status,
                requires_approval=receipt.requires_approval,
                approved_by=receipt.approved_by,
                supplier_reference=receipt.supplier_reference,
                document_reference=receipt.document_reference,
                reason=receipt.reason,
                notes=receipt.notes,
                store_id=receipt.store_id,
                created_at=receipt.received_at,
                item_count=len(receipt_items),
                total_quantity=sum(item.quantity for item in receipt_items),
            )
        )

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/receipts/{receipt_id}", response_model=ReceiptDetail)
def get_receipt_detail(
    receipt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        receipt_uuid = uuid.UUID(receipt_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Recebimento nao encontrado.") from None

    receipt = db.query(InventoryReceipt).filter(InventoryReceipt.id == receipt_uuid).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Recebimento nao encontrado.")
    ensure_store_access(current_user, receipt.store_id)

    receipt_items = get_receipt_items(db, receipt_uuid)
    movements = (
        db.query(StockMovement)
        .filter(StockMovement.receipt_group_id == receipt_uuid, StockMovement.movement_type == "entry")
        .order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
        .all()
    )
    movement_by_variant: dict[uuid.UUID, list[StockMovement]] = {}
    for movement in movements:
        movement_by_variant.setdefault(movement.variant_id, []).append(movement)
    audit_entries = (
        db.query(InventoryReceiptAuditLog)
        .filter(InventoryReceiptAuditLog.receipt_id == receipt_uuid)
        .order_by(InventoryReceiptAuditLog.created_at.desc(), InventoryReceiptAuditLog.id.desc())
        .all()
    )
    return ReceiptDetail(
        receipt_id=receipt_id,
        status=receipt.status,
        requires_approval=receipt.requires_approval,
        approved_by=receipt.approved_by,
        supplier_reference=receipt.supplier_reference,
        document_reference=receipt.document_reference,
        reason=receipt.reason,
        notes=receipt.notes,
        store_id=receipt.store_id,
        created_at=receipt.received_at,
        item_count=len(receipt_items),
        total_quantity=sum(item.quantity for item in receipt_items),
        items=[
            ReceiptMovementItem(
                receipt_item_id=item.id,
                movement_id=(movement_by_variant.get(item.variant_id) or [None])[0].id if movement_by_variant.get(item.variant_id) else None,
                variant_id=item.variant_id,
                quantity=item.quantity,
                created_at=item.created_at,
            )
            for item in receipt_items
        ],
        audit=[
            ReceiptAuditEntry(
                action=entry.action,
                details=entry.details,
                created_by=entry.created_by,
                created_at=entry.created_at,
            )
            for entry in audit_entries
        ],
    )


@router.get("/receipts-report", response_model=ReceiptDocumentReport)
def get_receipts_report(
    store_id: uuid.UUID | None = Query(default=None),
    created_from: date | None = Query(default=None),
    created_to: date | None = Query(default=None),
    q: str | None = Query(default=None),
    sort_by: str = Query(default="receipts"),
    direction: str = Query(default="desc"),
    limit: int = Query(default=12, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    receipt_query = db.query(InventoryReceipt)
    if store_id is not None:
        ensure_store_access(current_user, store_id)
        receipt_query = receipt_query.filter(InventoryReceipt.store_id == store_id)
    elif current_user.role != "admin":
        receipt_query = receipt_query.filter(InventoryReceipt.store_id == current_user.store_id)
    if created_from is not None:
        receipt_query = receipt_query.filter(
            InventoryReceipt.received_at >= datetime.combine(created_from, time.min, tzinfo=timezone.utc)
        )
    if created_to is not None:
        receipt_query = receipt_query.filter(
            InventoryReceipt.received_at < datetime.combine(created_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        )
    if q is not None:
        search = f"%{q.strip()}%"
        receipt_query = receipt_query.filter(
            or_(
                InventoryReceipt.supplier_reference.ilike(search),
                InventoryReceipt.document_reference.ilike(search),
            )
        )

    receipts = receipt_query.order_by(InventoryReceipt.received_at.desc()).all()
    effective_store_id = store_id if store_id is not None else current_user.store_id
    supplier_target_map = get_supplier_target_map(db, effective_store_id)
    upsert_supplier_risk_snapshots(
        db,
        store_id=effective_store_id,
        receipts=receipts,
        supplier_target_map=supplier_target_map,
    )
    db.commit()
    grouped: dict[tuple[str, str | None, bool], ReceiptDocumentReportEntry] = {}
    for receipt in receipts:
        key = (receipt.status, receipt.supplier_reference, bool(receipt.requires_approval))
        if key not in grouped:
            grouped[key] = ReceiptDocumentReportEntry(
                status=receipt.status,
                supplier_reference=receipt.supplier_reference,
                receipts=0,
                total_quantity=0,
                requires_approval=bool(receipt.requires_approval),
                pending_approval_receipts=0,
                approved_receipts=0,
                supplier_target_hours=supplier_target_map.get(receipt.supplier_reference or "Nao informado"),
            )
        grouped[key].receipts += 1
        grouped[key].total_quantity += sum(item.quantity for item in get_receipt_items(db, receipt.id))
        if receipt.requires_approval:
            if receipt.approved_by is None:
                grouped[key].pending_approval_receipts += 1
            else:
                grouped[key].approved_receipts += 1

    items = list(grouped.values())
    reverse = direction.lower() != "asc"
    if sort_by == "supplier":
        items.sort(key=lambda item: (item.supplier_reference or "", item.status, item.pending_approval_receipts), reverse=reverse)
    elif sort_by == "quantity":
        items.sort(key=lambda item: (item.total_quantity, item.receipts, item.pending_approval_receipts), reverse=reverse)
    elif sort_by == "status":
        items.sort(key=lambda item: (item.status, item.supplier_reference or "", item.pending_approval_receipts), reverse=reverse)
    elif sort_by == "approval":
        items.sort(key=lambda item: (item.pending_approval_receipts, item.approved_receipts, item.receipts), reverse=reverse)
    else:
        items.sort(key=lambda item: (item.receipts, item.total_quantity, item.pending_approval_receipts), reverse=reverse)

    total = len(items)
    paged_items = items[offset:offset + limit]

    return ReceiptDocumentReport(
        items=paged_items,
        total=total,
        limit=limit,
        offset=offset,
        created_from=datetime.combine(created_from, time.min, tzinfo=timezone.utc) if created_from else None,
        created_to=datetime.combine(created_to, time.min, tzinfo=timezone.utc) if created_to else None,
    )


@router.get("/supplier-risk-targets", response_model=list[SupplierRiskTargetResponse])
def list_supplier_risk_targets(
    store_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    effective_store_id = store_id if store_id is not None else current_user.store_id
    if effective_store_id is None:
        return []
    ensure_store_access(current_user, effective_store_id)
    return (
        db.query(InventorySupplierRiskTarget)
        .filter(InventorySupplierRiskTarget.store_id == effective_store_id)
        .order_by(InventorySupplierRiskTarget.supplier_reference.asc())
        .all()
    )


@router.put("/supplier-risk-targets", response_model=SupplierRiskTargetResponse)
def upsert_supplier_risk_target(
    payload: SupplierRiskTargetUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager")),
):
    ensure_store_access(current_user, payload.store_id)
    target = (
        db.query(InventorySupplierRiskTarget)
        .filter(
            InventorySupplierRiskTarget.store_id == payload.store_id,
            InventorySupplierRiskTarget.supplier_reference == payload.supplier_reference,
        )
        .first()
    )
    if not target:
        target = InventorySupplierRiskTarget(
            store_id=payload.store_id,
            supplier_reference=payload.supplier_reference,
        )
        db.add(target)
    target.target_hours = payload.target_hours
    target.updated_by = current_user.id
    db.commit()
    db.refresh(target)
    return target


@router.get("/supplier-risk-history", response_model=SupplierRiskHistoryResponse)
def list_supplier_risk_history(
    store_id: uuid.UUID | None = Query(default=None),
    supplier_reference: str | None = Query(default=None),
    created_from: date | None = Query(default=None),
    created_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    effective_store_id = store_id if store_id is not None else current_user.store_id
    if effective_store_id is None:
        return {"items": []}
    ensure_store_access(current_user, effective_store_id)
    query = db.query(InventorySupplierRiskSnapshot).filter(InventorySupplierRiskSnapshot.store_id == effective_store_id)
    if supplier_reference:
        query = query.filter(InventorySupplierRiskSnapshot.supplier_reference.ilike(f"%{supplier_reference.strip()}%"))
    if created_from:
        query = query.filter(InventorySupplierRiskSnapshot.snapshot_date >= created_from)
    if created_to:
        query = query.filter(InventorySupplierRiskSnapshot.snapshot_date <= created_to)
    items = query.order_by(
        InventorySupplierRiskSnapshot.snapshot_date.desc(),
        InventorySupplierRiskSnapshot.supplier_reference.asc(),
    ).all()
    return {
        "items": [
            SupplierRiskHistoryEntry(
                supplier_reference=item.supplier_reference,
                snapshot_date=datetime.combine(item.snapshot_date, time.min, tzinfo=timezone.utc),
                target_hours=item.target_hours,
                open_critical_count=item.open_critical_count,
                resolved_estimate_count=item.resolved_estimate_count,
            )
            for item in items
        ]
    }


@router.get("/supplier-risk-history/export")
def export_supplier_risk_history_csv(
    store_id: uuid.UUID | None = Query(default=None),
    supplier_reference: str | None = Query(default=None),
    created_from: date | None = Query(default=None),
    created_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    history = list_supplier_risk_history(
        store_id=store_id,
        supplier_reference=supplier_reference,
        created_from=created_from,
        created_to=created_to,
        db=db,
        current_user=current_user,
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["supplier_reference", "snapshot_date", "target_hours", "open_critical_count", "resolved_estimate_count"])
    for item in history["items"]:
        writer.writerow([
            item.supplier_reference,
            item.snapshot_date.isoformat(),
            item.target_hours,
            item.open_critical_count,
            item.resolved_estimate_count,
        ])

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="supplier-risk-history.csv"'},
    )


@router.get("/receipts-report/export")
def export_receipts_report_csv(
    store_id: uuid.UUID | None = Query(default=None),
    created_from: date | None = Query(default=None),
    created_to: date | None = Query(default=None),
    q: str | None = Query(default=None),
    sort_by: str = Query(default="receipts"),
    direction: str = Query(default="desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = get_receipts_report(
        store_id=store_id,
        created_from=created_from,
        created_to=created_to,
        q=q,
        sort_by=sort_by,
        direction=direction,
        limit=100,
        offset=0,
        db=db,
        current_user=current_user,
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "status",
        "supplier_reference",
        "requires_approval",
        "pending_approval_receipts",
        "approved_receipts",
        "receipts",
        "total_quantity",
    ])
    for item in report.items:
        writer.writerow([
            item.status,
            item.supplier_reference or "",
            item.requires_approval,
            item.pending_approval_receipts,
            item.approved_receipts,
            item.receipts,
            item.total_quantity,
        ])

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="receipts-report.csv"'},
    )


@router.post("/receipts/draft", response_model=ReceiptDetail)
def create_receipt_draft(
    payload: InventoryReceiptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager", "operator")),
):
    if not payload.items:
        raise HTTPException(status_code=400, detail="Informe ao menos um item para o recebimento.")

    ensure_store_access(current_user, payload.store_id)
    receipt_id = uuid.uuid4()
    actor_id = payload.created_by or current_user.id
    receipt = ensure_receipt_header(
        db,
        receipt_id=receipt_id,
        store_id=payload.store_id,
        supplier_reference=payload.supplier_reference,
        document_reference=payload.document_reference,
        reason=payload.reason,
        created_by=actor_id,
    )
    receipt.status = "draft"
    receipt.notes = payload.notes
    receipt.requires_approval = compute_requires_receipt_approval(payload.items)
    receipt.approved_by = None
    for item in payload.items:
        db.add(
            InventoryReceiptItem(
                receipt_id=receipt_id,
                variant_id=item.variant_id,
                quantity=item.quantity,
            )
        )
    add_receipt_audit_log(
        db,
        receipt_id=receipt_id,
        action="draft_created",
        created_by=actor_id,
        details=payload.document_reference or payload.supplier_reference or payload.reason,
    )
    record_audit_event(
        db,
        action="receipt.draft_created",
        entity_type="receipt",
        entity_id=receipt_id,
        store_id=payload.store_id,
        actor_id=actor_id,
        metadata={
            "item_count": len(payload.items),
            "total_quantity": sum(item.quantity for item in payload.items),
            "requires_approval": receipt.requires_approval,
        },
    )
    db.commit()
    return get_receipt_detail(receipt_id=str(receipt.id), db=db, current_user=current_user)


@router.put("/receipts/{receipt_id}/draft", response_model=ReceiptDetail)
def update_receipt_draft(
    receipt_id: str,
    payload: InventoryReceiptDraftUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager", "operator")),
):
    try:
        receipt_uuid = uuid.UUID(receipt_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Recebimento nao encontrado.") from None

    receipt = db.execute(
        select(InventoryReceipt).where(InventoryReceipt.id == receipt_uuid).with_for_update()
    ).scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Recebimento nao encontrado")
    ensure_receipt_draft_control(current_user, receipt)
    if receipt.status != "draft":
        raise HTTPException(status_code=409, detail="Somente rascunhos podem ser editados.")
    if not payload.items:
        raise HTTPException(status_code=400, detail="Informe ao menos um item para o rascunho.")

    receipt.supplier_reference = payload.supplier_reference
    receipt.document_reference = payload.document_reference
    receipt.reason = payload.reason
    receipt.notes = payload.notes
    receipt.requires_approval = compute_requires_receipt_approval(payload.items)
    receipt.approved_by = None if receipt.requires_approval else receipt.approved_by

    db.query(InventoryReceiptItem).filter(InventoryReceiptItem.receipt_id == receipt_uuid).delete()
    for item in payload.items:
        db.add(
            InventoryReceiptItem(
                receipt_id=receipt_uuid,
                variant_id=item.variant_id,
                quantity=item.quantity,
            )
        )
    add_receipt_audit_log(
        db,
        receipt_id=receipt_uuid,
        action="draft_updated",
        created_by=current_user.id,
        details=payload.document_reference or payload.supplier_reference or payload.reason,
    )

    db.commit()
    return get_receipt_detail(receipt_id=receipt_id, db=db, current_user=current_user)


@router.post("/receipts/{receipt_id}/post", response_model=ReceiptDetail)
def post_receipt_draft(
    receipt_id: str,
    x_receipt_bulk_confirmed: str | None = Header(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager", "operator")),
):
    try:
        receipt_uuid = uuid.UUID(receipt_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Recebimento nao encontrado.") from None

    receipt = db.execute(
        select(InventoryReceipt).where(InventoryReceipt.id == receipt_uuid).with_for_update()
    ).scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Recebimento nao encontrado")
    ensure_receipt_draft_control(current_user, receipt)
    if receipt.status != "draft":
        raise HTTPException(status_code=409, detail="Apenas recebimentos em rascunho podem ser efetivados.")
    if receipt.requires_approval and receipt.approved_by is None:
        raise HTTPException(status_code=409, detail="Este rascunho sensivel exige aprovacao antes da efetivacao.")

    receipt_items = get_receipt_items(db, receipt_uuid)
    if not receipt_items:
        raise HTTPException(status_code=400, detail="Rascunho sem itens para efetivar.")

    lock_inventory_balances(
        db,
        [(receipt.store_id, item.variant_id) for item in receipt_items],
        create_if_missing=True,
    )
    for item in receipt_items:
        change_stock(
            db,
            store_id=receipt.store_id,
            variant_id=item.variant_id,
            quantity_delta=item.quantity,
            movement_type="entry",
            reference_type="receipt_post",
            receipt_group_id=receipt_uuid,
            reference_id=item.id,
            supplier_reference=receipt.supplier_reference,
            document_reference=receipt.document_reference,
            reason=receipt.reason,
            created_by=current_user.id,
            create_if_missing=True,
        )

    receipt.status = "posted"
    if x_receipt_bulk_confirmed:
        add_receipt_audit_log(
            db,
            receipt_id=receipt_uuid,
            action="bulk_post_confirmed",
            created_by=current_user.id,
            details=x_receipt_bulk_confirmed,
        )
    add_receipt_audit_log(
        db,
        receipt_id=receipt_uuid,
        action="draft_posted",
        created_by=current_user.id,
        details=receipt.document_reference or receipt.supplier_reference or receipt.reason,
    )
    record_audit_event(
        db,
        action="receipt.posted",
        entity_type="receipt",
        entity_id=receipt_uuid,
        store_id=receipt.store_id,
        actor_id=current_user.id,
        metadata={
            "item_count": len(receipt_items),
            "total_quantity": sum(item.quantity for item in receipt_items),
        },
    )
    db.commit()
    return get_receipt_detail(receipt_id=receipt_id, db=db, current_user=current_user)


@router.post("/receipts/{receipt_id}/approve", response_model=ReceiptDetail)
def approve_receipt_draft(
    receipt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager")),
):
    try:
        receipt_uuid = uuid.UUID(receipt_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Recebimento nao encontrado.") from None

    receipt = db.execute(
        select(InventoryReceipt).where(InventoryReceipt.id == receipt_uuid).with_for_update()
    ).scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Recebimento nao encontrado")
    ensure_store_access(current_user, receipt.store_id)
    if receipt.status != "draft":
        raise HTTPException(status_code=409, detail="Somente rascunhos podem ser aprovados.")

    receipt.approved_by = current_user.id
    add_receipt_audit_log(
        db,
        receipt_id=receipt_uuid,
        action="draft_approved",
        created_by=current_user.id,
        details=receipt.document_reference or receipt.supplier_reference or receipt.reason,
    )
    record_audit_event(
        db,
        action="receipt.approved",
        entity_type="receipt",
        entity_id=receipt_uuid,
        store_id=receipt.store_id,
        actor_id=current_user.id,
    )
    db.commit()
    return get_receipt_detail(receipt_id=receipt_id, db=db, current_user=current_user)


@router.delete("/receipts/{receipt_id}/draft")
def discard_receipt_draft(
    receipt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager", "operator")),
):
    try:
        receipt_uuid = uuid.UUID(receipt_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Recebimento nao encontrado.") from None

    receipt = db.execute(
        select(InventoryReceipt).where(InventoryReceipt.id == receipt_uuid).with_for_update()
    ).scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Recebimento nao encontrado")
    ensure_receipt_draft_control(current_user, receipt)
    if receipt.status != "draft":
        raise HTTPException(status_code=409, detail="Somente rascunhos podem ser descartados.")

    db.query(InventoryReceiptItem).filter(InventoryReceiptItem.receipt_id == receipt_uuid).delete()
    db.query(InventoryReceiptAuditLog).filter(InventoryReceiptAuditLog.receipt_id == receipt_uuid).delete()
    db.query(InventoryReceipt).filter(InventoryReceipt.id == receipt_uuid).delete()
    db.commit()
    return {"status": "discarded", "receipt_id": receipt_id}


@router.post("/receipts/{receipt_id}/status", response_model=ReceiptDetail)
def update_receipt_status(
    receipt_id: str,
    payload: ReceiptStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager")),
):
    try:
        receipt_uuid = uuid.UUID(receipt_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Recebimento nao encontrado.") from None

    receipt = db.execute(
        select(InventoryReceipt).where(InventoryReceipt.id == receipt_uuid).with_for_update()
    ).scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Recebimento nao encontrado")

    ensure_store_access(current_user, receipt.store_id)
    next_status = payload.status.strip().lower()
    if next_status not in VALID_RECEIPT_STATUSES:
        raise HTTPException(status_code=400, detail="Status de recebimento invalido.")
    if receipt.status == "draft":
        raise HTTPException(status_code=409, detail="Use a efetivacao do rascunho para mover este recebimento.")
    if receipt.status == "canceled":
        raise HTTPException(status_code=409, detail="Recebimentos cancelados nao podem mudar de status.")
    if next_status == "canceled":
        raise HTTPException(status_code=400, detail="Use a operacao de cancelamento para cancelar o recebimento.")
    if next_status not in ALLOWED_RECEIPT_STATUS_TRANSITIONS.get(receipt.status, set()):
        raise HTTPException(status_code=409, detail="Transicao de status nao permitida para este recebimento.")

    receipt.status = next_status
    add_receipt_audit_log(
        db,
        receipt_id=receipt_uuid,
        action="status_updated",
        created_by=current_user.id,
        details=f"status={next_status}",
    )
    record_audit_event(
        db,
        action="receipt.status_updated",
        entity_type="receipt",
        entity_id=receipt_uuid,
        store_id=receipt.store_id,
        actor_id=current_user.id,
        metadata={"status": next_status},
    )
    db.commit()
    return get_receipt_detail(receipt_id=receipt_id, db=db, current_user=current_user)


@router.post("/receipts/{receipt_id}/cancel", response_model=ReceiptDetail)
def cancel_receipt(
    receipt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager")),
):
    try:
        receipt_uuid = uuid.UUID(receipt_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Recebimento nao encontrado.") from None

    receipt = db.execute(
        select(InventoryReceipt).where(InventoryReceipt.id == receipt_uuid).with_for_update()
    ).scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Recebimento nao encontrado")

    ensure_store_access(current_user, receipt.store_id)
    if receipt.status == "canceled":
        raise HTTPException(status_code=400, detail="Recebimento ja cancelado.")

    if receipt.status == "draft":
        raise HTTPException(status_code=409, detail="Rascunhos devem ser descartados ou editados, nao cancelados com estorno.")

    movements = (
        db.execute(
            select(StockMovement)
            .where(StockMovement.receipt_group_id == receipt_uuid, StockMovement.movement_type == "entry")
            .with_for_update()
        )
        .scalars()
        .all()
    )
    if not movements:
        raise HTTPException(status_code=400, detail="Recebimento sem itens para cancelar.")

    try:
        lock_inventory_balances(
            db,
            [(movement.store_id, movement.variant_id) for movement in movements],
        )
        for movement in movements:
            change_stock(
                db,
                store_id=movement.store_id,
                variant_id=movement.variant_id,
                quantity_delta=-movement.quantity_delta,
                movement_type="reversal",
                reference_type="receipt_cancel",
                receipt_group_id=receipt_uuid,
                reference_id=movement.id,
                supplier_reference=receipt.supplier_reference,
                document_reference=receipt.document_reference,
                reason="receipt_canceled",
                created_by=current_user.id,
            )
    except StockConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Estoque insuficiente para cancelar o recebimento.") from exc

    receipt.status = "canceled"
    add_receipt_audit_log(
        db,
        receipt_id=receipt_uuid,
        action="receipt_canceled",
        created_by=current_user.id,
        details=receipt.document_reference or receipt.supplier_reference or receipt.reason,
    )
    record_audit_event(
        db,
        action="receipt.canceled",
        entity_type="receipt",
        entity_id=receipt_uuid,
        store_id=receipt.store_id,
        actor_id=current_user.id,
        metadata={"movement_count": len(movements)},
    )
    db.commit()
    return get_receipt_detail(receipt_id=receipt_id, db=db, current_user=current_user)


@router.get("/receipts/{receipt_id}/export")
def export_receipt_csv(
    receipt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    detail = get_receipt_detail(receipt_id=receipt_id, db=db, current_user=current_user)

    items = (
        apply_movement_filters(
            db.query(StockMovement),
            current_user=current_user,
            store_id=detail.store_id,
            variant_id=None,
            movement_type="entry",
            reference_type=None,
            supplier_reference=detail.supplier_reference,
            document_reference=detail.document_reference,
            created_from=None,
            created_to=None,
        )
        .order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
        .all()
    )
    items = [item for item in items if build_receipt_id(item) == receipt_id]

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "receipt_id",
            "supplier_reference",
            "document_reference",
            "reason",
            "store_id",
            "movement_id",
            "variant_id",
            "quantity",
            "created_at",
        ]
    )
    for item in items:
        writer.writerow(
            [
                receipt_id,
                detail.supplier_reference or "",
                detail.document_reference or "",
                detail.reason or "",
                detail.store_id,
                item.id,
                item.variant_id,
                item.quantity_delta,
                item.created_at.isoformat(),
            ]
        )

    safe_receipt_id = receipt_id.replace("|", "-")
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="receipt-{safe_receipt_id}.csv"'},
    )


@router.post("/entry", response_model=InventoryBalanceResponse)
def create_inventory_entry(
    payload: InventoryEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager", "operator")),
):
    receipt_group_id = uuid.uuid4()
    actor_id = payload.created_by or current_user.id
    ensure_store_access(current_user, payload.store_id)
    receipt = ensure_receipt_header(
        db,
        receipt_id=receipt_group_id,
        store_id=payload.store_id,
        supplier_reference=payload.supplier_reference,
        document_reference=payload.document_reference,
        reason=payload.reason,
        created_by=actor_id,
    )
    receipt.status = "posted"
    receipt.notes = None
    db.add(
        InventoryReceiptItem(
            receipt_id=receipt_group_id,
            variant_id=payload.variant_id,
            quantity=payload.quantity,
        )
    )

    balance = change_stock(
        db,
        store_id=payload.store_id,
        variant_id=payload.variant_id,
        quantity_delta=payload.quantity,
        movement_type="entry",
        reference_type="manual_entry",
        receipt_group_id=receipt_group_id,
        supplier_reference=payload.supplier_reference,
        document_reference=payload.document_reference,
        reason=payload.reason,
        created_by=actor_id,
        create_if_missing=True,
    )
    add_receipt_audit_log(
        db,
        receipt_id=receipt_group_id,
        action="direct_receipt_created",
        created_by=actor_id,
        details=payload.document_reference or payload.supplier_reference or payload.reason,
    )
    record_audit_event(
        db,
        action="receipt.created",
        entity_type="receipt",
        entity_id=receipt_group_id,
        store_id=payload.store_id,
        actor_id=actor_id,
        metadata={"item_count": 1, "total_quantity": payload.quantity},
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Loja, variante ou usuario informado nao foi encontrado.",
        ) from None

    db.refresh(balance)
    return balance


@router.post("/entries", response_model=InventoryBatchEntryResponse)
def create_inventory_batch_entry(
    payload: InventoryBatchEntryCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager", "operator")),
):
    if not payload.items:
        raise HTTPException(status_code=400, detail="Informe ao menos um item para o recebimento.")

    ensure_store_access(current_user, payload.store_id)
    if idempotency_key is not None:
        idempotency_key = idempotency_key.strip()
        if not idempotency_key or len(idempotency_key) > 120:
            raise HTTPException(status_code=400, detail="Idempotency-Key deve ter entre 1 e 120 caracteres.")
        existing_receipt = (
            db.query(InventoryReceipt)
            .filter(
                InventoryReceipt.store_id == payload.store_id,
                InventoryReceipt.idempotency_key == idempotency_key,
            )
            .first()
        )
        if existing_receipt:
            existing_items = get_receipt_items(db, existing_receipt.id)
            ensure_matching_batch_receipt(existing_receipt, existing_items, payload)
            balances = lock_inventory_balances(
                db,
                [(payload.store_id, item.variant_id) for item in existing_items],
            )
            return {"store_id": payload.store_id, "balances": list(balances.values())}
    updated_balances: list[InventoryBalance] = []

    try:
        actor_id = payload.created_by or current_user.id
        receipt_group_id = uuid.uuid4()
        receipt = ensure_receipt_header(
            db,
            receipt_id=receipt_group_id,
            store_id=payload.store_id,
            supplier_reference=payload.supplier_reference,
            document_reference=payload.document_reference,
            reason=payload.reason,
            created_by=actor_id,
        )
        receipt.status = "posted"
        receipt.notes = None
        receipt.idempotency_key = idempotency_key
        lock_inventory_balances(
            db,
            [(payload.store_id, item.variant_id) for item in payload.items],
            create_if_missing=True,
        )
        for item in payload.items:
            db.add(
                InventoryReceiptItem(
                    receipt_id=receipt_group_id,
                    variant_id=item.variant_id,
                    quantity=item.quantity,
                )
            )
            balance = change_stock(
                db,
                store_id=payload.store_id,
                variant_id=item.variant_id,
                quantity_delta=item.quantity,
                movement_type="entry",
                reference_type="batch_entry",
                receipt_group_id=receipt_group_id,
                supplier_reference=payload.supplier_reference,
                document_reference=payload.document_reference,
                reason=payload.reason,
                created_by=actor_id,
                create_if_missing=True,
            )
            updated_balances.append(balance)
        add_receipt_audit_log(
            db,
            receipt_id=receipt_group_id,
            action="batch_receipt_created",
            created_by=actor_id,
            details=payload.document_reference or payload.supplier_reference or payload.reason,
        )
        record_audit_event(
            db,
            action="receipt.created",
            entity_type="receipt",
            entity_id=receipt_group_id,
            store_id=payload.store_id,
            actor_id=actor_id,
            metadata={
                "item_count": len(payload.items),
                "total_quantity": sum(item.quantity for item in payload.items),
            },
        )

        db.commit()
    except IntegrityError:
        db.rollback()
        if idempotency_key:
            existing_receipt = (
                db.query(InventoryReceipt)
                .filter(
                    InventoryReceipt.store_id == payload.store_id,
                    InventoryReceipt.idempotency_key == idempotency_key,
                )
                .first()
            )
            if existing_receipt:
                existing_items = get_receipt_items(db, existing_receipt.id)
                ensure_matching_batch_receipt(existing_receipt, existing_items, payload)
                balances = lock_inventory_balances(
                    db,
                    [(payload.store_id, item.variant_id) for item in existing_items],
                )
                return {"store_id": payload.store_id, "balances": list(balances.values())}
        raise HTTPException(
            status_code=400,
            detail="Loja, variante ou usuario informado nao foi encontrado.",
        ) from None

    for balance in updated_balances:
        db.refresh(balance)

    return {
        "store_id": payload.store_id,
        "balances": updated_balances,
    }


@router.post("/adjustment", response_model=InventoryBalanceResponse)
def create_inventory_adjustment(
    payload: InventoryAdjustmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager")),
):
    ensure_store_access(current_user, payload.store_id)
    balance, delta = set_stock_quantity(
        db,
        store_id=payload.store_id,
        variant_id=payload.variant_id,
        quantity=payload.new_quantity,
        reference_type="manual_adjustment",
        reason=payload.reason,
        created_by=payload.created_by or current_user.id,
    )

    if delta == 0:
        raise HTTPException(status_code=400, detail="O novo saldo e igual ao saldo atual.")

    actor_id = payload.created_by or current_user.id
    record_audit_event(
        db,
        action="inventory.adjusted",
        entity_type="inventory_balance",
        entity_id=balance.id,
        store_id=payload.store_id,
        actor_id=actor_id,
        metadata={
            "variant_id": str(payload.variant_id),
            "quantity_delta": delta,
            "new_quantity": payload.new_quantity,
        },
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Loja, variante ou usuario informado nao foi encontrado.",
        ) from None

    db.refresh(balance)
    return balance


@router.post("/transfer")
def create_inventory_transfer(
    payload: InventoryTransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager")),
):
    if payload.source_store_id == payload.destination_store_id:
        raise HTTPException(
            status_code=400,
            detail="A loja de origem e destino precisam ser diferentes.",
        )

    ensure_store_access(current_user, payload.source_store_id)
    ensure_store_access(current_user, payload.destination_store_id)

    try:
        actor_id = payload.created_by or current_user.id
        lock_inventory_balances(
            db,
            [
                (payload.source_store_id, payload.variant_id),
                (payload.destination_store_id, payload.variant_id),
            ],
            create_if_missing=True,
        )
        source_balance = change_stock(
            db,
            store_id=payload.source_store_id,
            variant_id=payload.variant_id,
            quantity_delta=-payload.quantity,
            movement_type="transfer_out",
            reference_type="store_transfer",
            reference_id=payload.destination_store_id,
            reason=payload.reason,
            created_by=actor_id,
        )
        destination_balance = change_stock(
            db,
            store_id=payload.destination_store_id,
            variant_id=payload.variant_id,
            quantity_delta=payload.quantity,
            movement_type="transfer_in",
            reference_type="store_transfer",
            reference_id=payload.source_store_id,
            reason=payload.reason,
            created_by=actor_id,
            create_if_missing=True,
        )

        record_audit_event(
            db,
            action="inventory.transferred",
            entity_type="inventory_balance",
            entity_id=source_balance.id,
            store_id=payload.source_store_id,
            actor_id=actor_id,
            metadata={
                "variant_id": str(payload.variant_id),
                "destination_store_id": str(payload.destination_store_id),
                "quantity": payload.quantity,
            },
        )

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except StockConflictError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Estoque insuficiente na loja de origem para concluir a transferencia.",
        ) from exc
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Loja, variante ou usuario informado nao foi encontrado.",
        ) from None

    db.refresh(source_balance)
    db.refresh(destination_balance)

    return {
        "source_balance": InventoryBalanceResponse.model_validate(source_balance),
        "destination_balance": InventoryBalanceResponse.model_validate(destination_balance),
    }
