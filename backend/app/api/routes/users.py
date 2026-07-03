import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, get_password_hash, require_roles
from app.models.user import User
from app.schemas.auth import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserResponse)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role=payload.role,
        is_active=payload.is_active,
        store_id=payload.store_id,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Email ja existe ou a loja informada nao foi encontrada.",
        ) from None

    db.refresh(user)
    return user


@router.get("/", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(User)
    if current_user.role != "admin":
        query = query.filter(User.store_id == current_user.store_id)
    return query.order_by(User.name.asc()).all()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado.")
    if current_user.role != "admin" and current_user.store_id != user.store_id:
        raise HTTPException(status_code=403, detail="Usuario sem acesso a este usuario.")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado.")

    if current_user.role != "admin" and current_user.store_id != user.store_id:
        raise HTTPException(status_code=403, detail="Usuario sem acesso a este usuario.")

    updates = payload.model_dump(exclude_unset=True)
    password = updates.pop("password", None)

    if current_user.role != "admin":
        updates.pop("role", None)
        updates.pop("store_id", None)

    for field, value in updates.items():
        setattr(user, field, value)

    if password:
        user.password_hash = get_password_hash(password)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Email ja existe ou a loja informada nao foi encontrada.",
        ) from None

    db.refresh(user)
    return user
