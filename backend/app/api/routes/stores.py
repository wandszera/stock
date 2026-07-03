import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.store import Store
from app.models.user import User
from app.schemas.store import StoreCreate, StoreResponse, StoreUpdate

router = APIRouter(prefix="/stores", tags=["stores"])


@router.post("/", response_model=StoreResponse)
def create_store(
    payload: StoreCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    store = Store(**payload.model_dump())
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.get("/", response_model=list[StoreResponse])
def list_stores(
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Store)

    if current_user.role != "admin":
        query = query.filter(Store.id == current_user.store_id)
    if is_active is not None:
        query = query.filter(Store.is_active == is_active)

    return query.order_by(Store.name.asc()).all()


@router.get("/{store_id}", response_model=StoreResponse)
def get_store(
    store_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Loja nao encontrada.")
    if current_user.role != "admin" and current_user.store_id != store.id:
        raise HTTPException(status_code=403, detail="Usuario sem acesso a esta loja.")
    return store


@router.patch("/{store_id}", response_model=StoreResponse)
def update_store(
    store_id: uuid.UUID,
    payload: StoreUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Loja nao encontrada.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(store, field, value)

    db.commit()
    db.refresh(store)
    return store
