from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
)
from app.models.user import User
from app.schemas.auth import AuthResponse, BootstrapAdminCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/bootstrap", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def bootstrap_admin(payload: BootstrapAdminCreate, db: Session = Depends(get_db)):
    has_users = db.query(User.id).first()
    if has_users:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bootstrap ja foi executado. Use o login normal.",
        )

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role="admin",
        is_active=True,
        store_id=payload.store_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return AuthResponse(
        access_token=create_access_token(user),
        user=user,
    )


@router.post("/login", response_model=AuthResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha invalidos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthResponse(
        access_token=create_access_token(user),
        user=user,
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user
