"""Opt-in concurrency tests that require a dedicated PostgreSQL database."""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

import app.models  # noqa: F401 - registers every mapped table
from app.models.base import Base
from app.models.inventory import InventoryBalance, StockMovement
from app.models.product import Product, ProductVariant
from app.models.store import Store
from app.services.inventory import StockConflictError, change_stock


POSTGRES_TEST_URL = os.getenv("TEST_POSTGRES_DATABASE_URL")


@pytest.mark.postgres
@pytest.mark.skipif(
    not POSTGRES_TEST_URL,
    reason="Defina TEST_POSTGRES_DATABASE_URL para executar o teste de concorrencia real.",
)
def test_concurrent_stock_decrements_allow_only_one_winner():
    schema = f"stock_test_{uuid.uuid4().hex}"
    admin_engine = create_engine(POSTGRES_TEST_URL, pool_pre_ping=True)

    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    test_engine = admin_engine.execution_options(schema_translate_map={None: schema})
    try:
        Base.metadata.create_all(test_engine)
        with Session(test_engine) as session:
            store = Store(name="Loja Concorrente")
            product = Product(name="Produto Concorrente")
            session.add_all([store, product])
            session.flush()
            variant = ProductVariant(
                product_id=product.id,
                sku=f"CONCURRENT-{uuid.uuid4().hex[:8]}",
                cost_price=10,
                sale_price=20,
            )
            session.add(variant)
            session.flush()
            session.add(
                InventoryBalance(
                    store_id=store.id,
                    variant_id=variant.id,
                    on_hand_qty=1,
                    reserved_qty=0,
                )
            )
            session.commit()
            store_id = store.id
            variant_id = variant.id

        start = Barrier(2)

        def decrement_once():
            with Session(test_engine) as session:
                start.wait(timeout=10)
                try:
                    change_stock(
                        session,
                        store_id=store_id,
                        variant_id=variant_id,
                        quantity_delta=-1,
                        movement_type="sale",
                        reference_type="concurrency_test",
                        created_by=None,
                    )
                    session.commit()
                    return "committed"
                except StockConflictError:
                    session.rollback()
                    return "conflict"

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: decrement_once(), range(2)))

        assert sorted(results) == ["committed", "conflict"]
        with Session(test_engine) as session:
            balance = session.query(InventoryBalance).filter_by(
                store_id=store_id, variant_id=variant_id
            ).one()
            assert balance.on_hand_qty == 0
            assert session.query(StockMovement).filter_by(
                reference_type="concurrency_test"
            ).count() == 1
    finally:
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin_engine.dispose()
