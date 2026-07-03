import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.product import ProductVariant
from app.models.user import User
from app.schemas.product import VariantCreate, VariantResponse, VariantUpdate

router = APIRouter(prefix="/variants", tags=["variants"])


@router.post("/", response_model=VariantResponse)
def create_variant(
    payload: VariantCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "manager")),
):
    variant = ProductVariant(**payload.model_dump())
    db.add(variant)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="SKU ou codigo de barras ja existe, ou o produto informado nao foi encontrado.",
        ) from None
    db.refresh(variant)
    return variant


@router.get("/", response_model=list[VariantResponse])
def list_variants(
    product_id: uuid.UUID | None = Query(default=None),
    sku: str | None = Query(default=None),
    barcode: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(ProductVariant)

    if product_id is not None:
        query = query.filter(ProductVariant.product_id == product_id)
    if sku:
        query = query.filter(ProductVariant.sku == sku.strip())
    if barcode:
        query = query.filter(ProductVariant.barcode == barcode.strip())

    return query.order_by(ProductVariant.sku.asc()).all()


@router.get("/{variant_id}", response_model=VariantResponse)
def get_variant(
    variant_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    variant = db.query(ProductVariant).filter(ProductVariant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variante nao encontrada.")
    return variant


@router.patch("/{variant_id}", response_model=VariantResponse)
def update_variant(
    variant_id: uuid.UUID,
    payload: VariantUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "manager")),
):
    variant = db.query(ProductVariant).filter(ProductVariant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variante nao encontrada.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(variant, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="SKU ou codigo de barras ja existe, ou o produto informado nao foi encontrado.",
        ) from None

    db.refresh(variant)
    return variant
