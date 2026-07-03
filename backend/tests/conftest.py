import uuid
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models
from app.core.database import get_db
from app.core.security import get_password_hash
from app.main import app
from app.models.base import Base
from app.models.inventory import InventoryBalance
from app.models.product import Product, ProductVariant
from app.models.store import Store
from app.models.user import User


@pytest.fixture()
def engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session(engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_store(db_session, name: str) -> Store:
    store = Store(name=name)
    db_session.add(store)
    db_session.commit()
    db_session.refresh(store)
    return store


def create_user(
    db_session,
    *,
    email: str,
    password: str,
    role: str,
    store_id=None,
    is_active: bool = True,
) -> User:
    user = User(
        name=email.split("@")[0],
        email=email,
        password_hash=get_password_hash(password),
        role=role,
        is_active=is_active,
        store_id=store_id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_variant_with_balance(db_session, *, store_id, on_hand_qty: int = 10):
    product = Product(name=f"Produto {uuid.uuid4().hex[:6]}")
    db_session.add(product)
    db_session.flush()

    variant = ProductVariant(
        product_id=product.id,
        sku=f"SKU-{uuid.uuid4().hex[:8]}",
        cost_price=10,
        sale_price=20,
    )
    db_session.add(variant)
    db_session.flush()

    balance = InventoryBalance(
        store_id=store_id,
        variant_id=variant.id,
        on_hand_qty=on_hand_qty,
        reserved_qty=0,
    )
    db_session.add(balance)
    db_session.commit()
    db_session.refresh(variant)
    return variant, balance


@pytest.fixture()
def store_factory(db_session):
    return lambda name: create_store(db_session, name)


@pytest.fixture()
def user_factory(db_session):
    def _make(**kwargs):
        return create_user(db_session, **kwargs)

    return _make


@pytest.fixture()
def stock_factory(db_session):
    def _make(**kwargs):
        return create_variant_with_balance(db_session, **kwargs)

    return _make


@pytest.fixture()
def auth_headers(client, db_session):
    def _make(email: str, password: str, role: str, store_id=None):
        create_user(
            db_session,
            email=email,
            password=password,
            role=role,
            store_id=store_id,
        )
        response = client.post(
            "/auth/login",
            data={"username": email, "password": password},
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _make
