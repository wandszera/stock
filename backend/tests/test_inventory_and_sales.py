import uuid
from datetime import datetime, timedelta, timezone

from app.models.inventory import InventoryBalance, InventoryReceipt, InventoryReceiptAuditLog, InventoryReceiptItem, InventorySupplierRiskSnapshot, InventorySupplierRiskTarget, StockMovement
from app.models.product import Product, ProductVariant
from app.models.sale import Sale


def test_inventory_balances_are_filtered_by_user_store(client, auth_headers, store_factory, stock_factory):
    store_a = store_factory("Loja A")
    store_b = store_factory("Loja B")
    stock_factory(store_id=store_a.id, on_hand_qty=5)
    stock_factory(store_id=store_b.id, on_hand_qty=9)

    headers = auth_headers(
        "operator@loja-a.com",
        "secret123",
        "operator",
        store_id=store_a.id,
    )

    response = client.get("/inventory/balances", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["store_id"] == str(store_a.id)


def test_admin_can_filter_inventory_balances_by_store(client, auth_headers, store_factory, stock_factory):
    store_a = store_factory("Loja A")
    store_b = store_factory("Loja B")
    stock_factory(store_id=store_a.id, on_hand_qty=5)
    stock_factory(store_id=store_b.id, on_hand_qty=9)
    admin_headers = auth_headers("admin@rede.com", "secret123", "admin")

    response = client.get(f"/inventory/balances?store_id={store_b.id}", headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["store_id"] == str(store_b.id)


def test_sale_decrements_stock_and_cancel_restores_balance(client, db_session, auth_headers, store_factory, stock_factory):
    store = store_factory("Loja Principal")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=10)
    headers = auth_headers(
        "manager@loja.com",
        "secret123",
        "manager",
        store_id=store.id,
    )

    sale_response = client.post(
        "/sales/",
        headers=headers,
        json={
            "store_id": str(store.id),
            "items": [
                {
                    "variant_id": str(variant.id),
                    "quantity": 3,
                    "unit_price": "20.00",
                }
            ],
        },
    )

    assert sale_response.status_code == 200
    sale_id = sale_response.json()["id"]

    updated_balance = (
        db_session.query(InventoryBalance)
        .filter(InventoryBalance.store_id == store.id, InventoryBalance.variant_id == variant.id)
        .one()
    )
    assert updated_balance.on_hand_qty == 7

    cancel_response = client.post(f"/sales/{sale_id}/cancel", headers=headers)

    assert cancel_response.status_code == 200
    db_session.expire_all()
    restored_balance = (
        db_session.query(InventoryBalance)
        .filter(InventoryBalance.store_id == store.id, InventoryBalance.variant_id == variant.id)
        .one()
    )
    sale = db_session.query(Sale).filter(Sale.id == uuid.UUID(sale_id)).one()

    assert restored_balance.on_hand_qty == 10
    assert sale.status == "canceled"


def test_sales_history_lists_and_details_sale_items(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Historico")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=10)
    headers = auth_headers(
        "manager@historico.com",
        "secret123",
        "manager",
        store_id=store.id,
    )

    create_response = client.post(
        "/sales/",
        headers=headers,
        json={
            "store_id": str(store.id),
            "discount_amount": "5.00",
            "items": [
                {
                    "variant_id": str(variant.id),
                    "quantity": 2,
                    "unit_price": "20.00",
                }
            ],
        },
    )

    assert create_response.status_code == 200
    sale_id = create_response.json()["id"]

    list_response = client.get("/sales/", headers=headers)

    assert list_response.status_code == 200
    sales = list_response.json()
    assert sales["total"] == 1
    assert sales["limit"] == 12
    assert sales["offset"] == 0
    assert len(sales["items"]) == 1
    assert sales["items"][0]["id"] == sale_id
    assert sales["items"][0]["discount_amount"] == "5.00"
    assert sales["items"][0]["total_amount"] == "35.00"
    assert len(sales["items"][0]["items"]) == 1
    assert sales["items"][0]["items"][0]["variant_id"] == str(variant.id)
    assert sales["items"][0]["items"][0]["line_total"] == "40.00"

    detail_response = client.get(f"/sales/{sale_id}", headers=headers)

    assert detail_response.status_code == 200
    sale = detail_response.json()
    assert sale["id"] == sale_id
    assert sale["store_id"] == str(store.id)
    assert sale["sold_at"] is not None
    assert sale["items"][0]["quantity"] == 2


def test_sales_history_respects_store_scope_for_non_admin(
    client, auth_headers, store_factory, stock_factory
):
    store_a = store_factory("Loja A")
    store_b = store_factory("Loja B")
    variant, _ = stock_factory(store_id=store_b.id, on_hand_qty=10)

    manager_headers = auth_headers(
        "manager@loja-a.com",
        "secret123",
        "manager",
        store_id=store_a.id,
    )
    admin_headers = auth_headers("admin@rede.com", "secret123", "admin")

    create_response = client.post(
        "/sales/",
        headers=admin_headers,
        json={
            "store_id": str(store_b.id),
            "items": [
                {
                    "variant_id": str(variant.id),
                    "quantity": 1,
                    "unit_price": "20.00",
                }
            ],
        },
    )

    assert create_response.status_code == 200
    sale_id = create_response.json()["id"]

    list_response = client.get(f"/sales/?store_id={store_b.id}", headers=manager_headers)
    detail_response = client.get(f"/sales/{sale_id}", headers=manager_headers)

    assert list_response.status_code == 403
    assert detail_response.status_code == 403


def test_sales_history_supports_limit_and_offset_pagination(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Paginada")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=10)
    headers = auth_headers("manager@paginada.com", "secret123", "manager", store_id=store.id)

    for _ in range(3):
        response = client.post(
            "/sales/",
            headers=headers,
            json={
                "store_id": str(store.id),
                "items": [
                    {
                        "variant_id": str(variant.id),
                        "quantity": 1,
                        "unit_price": "20.00",
                    }
                ],
            },
        )
        assert response.status_code == 200

    paged_response = client.get("/sales/?limit=2&offset=1", headers=headers)

    assert paged_response.status_code == 200
    body = paged_response.json()
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert len(body["items"]) == 2


def test_inventory_movements_support_limit_and_offset_pagination(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Movimentos")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=12)
    headers = auth_headers("manager@movimentos.com", "secret123", "manager", store_id=store.id)

    entry_response = client.post(
        "/inventory/entry",
        headers=headers,
        json={
            "store_id": str(store.id),
            "variant_id": str(variant.id),
            "quantity": 2,
            "reason": "reposicao",
        },
    )
    assert entry_response.status_code == 200

    adjustment_response = client.post(
        "/inventory/adjustment",
        headers=headers,
        json={
            "store_id": str(store.id),
            "variant_id": str(variant.id),
            "new_quantity": 10,
            "reason": "acerto operacional",
        },
    )
    assert adjustment_response.status_code == 200

    movements_response = client.get("/inventory/movements?limit=1&offset=1", headers=headers)

    assert movements_response.status_code == 200
    body = movements_response.json()
    assert body["total"] == 2
    assert body["limit"] == 1
    assert body["offset"] == 1
    assert len(body["items"]) == 1


def test_sales_history_can_be_filtered_by_period(
    client, db_session, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Periodo")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=10)
    headers = auth_headers("manager@periodo.com", "secret123", "manager", store_id=store.id)

    first_sale = client.post(
        "/sales/",
        headers=headers,
        json={
            "store_id": str(store.id),
            "items": [{"variant_id": str(variant.id), "quantity": 1, "unit_price": "20.00"}],
        },
    )
    second_sale = client.post(
        "/sales/",
        headers=headers,
        json={
            "store_id": str(store.id),
            "items": [{"variant_id": str(variant.id), "quantity": 1, "unit_price": "20.00"}],
        },
    )
    assert first_sale.status_code == 200
    assert second_sale.status_code == 200

    old_sale = db_session.query(Sale).filter(Sale.id == uuid.UUID(first_sale.json()["id"])).one()
    recent_sale = db_session.query(Sale).filter(Sale.id == uuid.UUID(second_sale.json()["id"])).one()
    old_sale.sold_at = datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc)
    recent_sale.sold_at = datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc)
    db_session.commit()

    response = client.get("/sales/?sold_from=2026-04-19&sold_to=2026-04-20", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == second_sale.json()["id"]


def test_sales_history_can_be_filtered_by_variant_sku_or_product_name(
    client, auth_headers, store_factory, db_session
):
    store = store_factory("Loja Busca Vendas")
    headers = auth_headers("manager@busca-vendas.com", "secret123", "manager", store_id=store.id)

    product_a = Product(name="Tenis Nimbus")
    product_b = Product(name="Mochila Trail")
    db_session.add_all([product_a, product_b])
    db_session.flush()

    variant_a = ProductVariant(
        product_id=product_a.id,
        sku="TENIS-NIM-42",
        barcode="7890000000011",
        cost_price="100.00",
        sale_price="150.00",
    )
    variant_b = ProductVariant(
        product_id=product_b.id,
        sku="MOCH-TRAIL-01",
        barcode="7890000000012",
        cost_price="80.00",
        sale_price="130.00",
    )
    db_session.add_all([variant_a, variant_b])
    db_session.flush()

    db_session.add_all(
        [
            InventoryBalance(store_id=store.id, variant_id=variant_a.id, on_hand_qty=10, reserved_qty=0),
            InventoryBalance(store_id=store.id, variant_id=variant_b.id, on_hand_qty=10, reserved_qty=0),
        ]
    )
    db_session.commit()

    first_sale = client.post(
        "/sales/",
        headers=headers,
        json={
            "store_id": str(store.id),
            "items": [{"variant_id": str(variant_a.id), "quantity": 1, "unit_price": "150.00"}],
        },
    )
    second_sale = client.post(
        "/sales/",
        headers=headers,
        json={
            "store_id": str(store.id),
            "items": [{"variant_id": str(variant_b.id), "quantity": 1, "unit_price": "130.00"}],
        },
    )

    assert first_sale.status_code == 200
    assert second_sale.status_code == 200

    sku_response = client.get("/sales/?q=TENIS-NIM", headers=headers)
    product_response = client.get("/sales/?q=Trail", headers=headers)

    assert sku_response.status_code == 200
    assert product_response.status_code == 200
    assert sku_response.json()["total"] == 1
    assert sku_response.json()["items"][0]["id"] == first_sale.json()["id"]
    assert product_response.json()["total"] == 1
    assert product_response.json()["items"][0]["id"] == second_sale.json()["id"]


def test_inventory_movements_can_be_filtered_by_period(
    client, db_session, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Movimento Periodo")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=10)
    headers = auth_headers("manager@mov-periodo.com", "secret123", "manager", store_id=store.id)

    first_entry = client.post(
        "/inventory/entry",
        headers=headers,
        json={"store_id": str(store.id), "variant_id": str(variant.id), "quantity": 1, "reason": "primeiro"},
    )
    second_entry = client.post(
        "/inventory/entry",
        headers=headers,
        json={"store_id": str(store.id), "variant_id": str(variant.id), "quantity": 2, "reason": "segundo"},
    )
    assert first_entry.status_code == 200
    assert second_entry.status_code == 200

    movements = db_session.query(StockMovement).filter(StockMovement.store_id == store.id).order_by(StockMovement.created_at.asc()).all()
    movements[0].created_at = datetime(2026, 4, 16, 10, 0, tzinfo=timezone.utc)
    movements[1].created_at = datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc)
    db_session.commit()

    response = client.get("/inventory/movements?created_from=2026-04-19&created_to=2026-04-20", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["reason"] == "segundo"


def test_inventory_batch_entry_updates_multiple_balances(
    client, db_session, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Recebimento")
    variant_a, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    variant_b, _ = stock_factory(store_id=store.id, on_hand_qty=7)
    headers = auth_headers("operator@recebimento.com", "secret123", "operator", store_id=store.id)

    response = client.post(
        "/inventory/entries",
        headers=headers,
        json={
            "store_id": str(store.id),
            "reason": "nf 123",
            "items": [
                {"variant_id": str(variant_a.id), "quantity": 3},
                {"variant_id": str(variant_b.id), "quantity": 2},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["store_id"] == str(store.id)
    assert len(body["balances"]) == 2

    db_session.expire_all()
    balances = (
        db_session.query(InventoryBalance)
        .filter(InventoryBalance.store_id == store.id)
        .order_by(InventoryBalance.variant_id.asc())
        .all()
    )
    assert sorted(balance.on_hand_qty for balance in balances) == [8, 9]


def test_inventory_batch_entry_persists_supplier_and_document_references(
    client, db_session, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Referencias")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    headers = auth_headers("operator@referencias.com", "secret123", "operator", store_id=store.id)

    response = client.post(
        "/inventory/entries",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Azul",
            "document_reference": "NF-2026-0042",
            "reason": "recebimento conferido",
            "items": [
                {"variant_id": str(variant.id), "quantity": 3},
            ],
        },
    )

    assert response.status_code == 200

    db_session.expire_all()
    movement = (
        db_session.query(StockMovement)
        .filter(
            StockMovement.store_id == store.id,
            StockMovement.variant_id == variant.id,
            StockMovement.reference_type == "batch_entry",
        )
        .one()
    )

    assert movement.supplier_reference == "Fornecedor Azul"
    assert movement.document_reference == "NF-2026-0042"
    assert movement.reason == "recebimento conferido"
    receipt = db_session.query(InventoryReceipt).filter(InventoryReceipt.id == movement.receipt_group_id).one()
    assert receipt.status == "posted"
    assert receipt.document_reference == "NF-2026-0042"


def test_inventory_movements_can_be_filtered_by_supplier_and_document_reference(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Filtros")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    headers = auth_headers("manager@filtros.com", "secret123", "manager", store_id=store.id)

    first_entry = client.post(
        "/inventory/entries",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Norte",
            "document_reference": "NF-100",
            "reason": "primeiro lote",
            "items": [{"variant_id": str(variant.id), "quantity": 2}],
        },
    )
    second_entry = client.post(
        "/inventory/entries",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Sul",
            "document_reference": "NF-200",
            "reason": "segundo lote",
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
        },
    )
    assert first_entry.status_code == 200
    assert second_entry.status_code == 200

    response = client.get(
        "/inventory/movements?supplier_reference=norte&document_reference=NF-100",
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["supplier_reference"] == "Fornecedor Norte"
    assert body["items"][0]["document_reference"] == "NF-100"


def test_inventory_movements_export_csv_returns_current_filtered_snapshot(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja CSV")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    headers = auth_headers("manager@csv.com", "secret123", "manager", store_id=store.id)

    response = client.post(
        "/inventory/entries",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor CSV",
            "document_reference": "ROM-55",
            "reason": "lote exportavel",
            "items": [{"variant_id": str(variant.id), "quantity": 2}],
        },
    )
    assert response.status_code == 200

    export_response = client.get(
        "/inventory/movements/export?supplier_reference=CSV&document_reference=ROM-55",
        headers=headers,
    )

    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=" in export_response.headers["content-disposition"]

    csv_body = export_response.text
    assert "supplier_reference" in csv_body
    assert "document_reference" in csv_body
    assert "Fornecedor CSV" in csv_body
    assert "ROM-55" in csv_body


def test_recent_receipt_references_group_latest_receipts_for_reuse(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Reuso")
    variant_a, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    variant_b, _ = stock_factory(store_id=store.id, on_hand_qty=7)
    headers = auth_headers("manager@reuso.com", "secret123", "manager", store_id=store.id)

    first_response = client.post(
        "/inventory/entries",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Reuso",
            "document_reference": "NF-777",
            "reason": "recebimento semanal",
            "items": [
                {"variant_id": str(variant_a.id), "quantity": 2},
                {"variant_id": str(variant_b.id), "quantity": 3},
            ],
        },
    )
    second_response = client.post(
        "/inventory/entries",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Extra",
            "document_reference": "NF-888",
            "reason": "reposicao urgente",
            "items": [
                {"variant_id": str(variant_a.id), "quantity": 1},
            ],
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    response = client.get("/inventory/receipt-references", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["supplier_reference"] == "Fornecedor Extra"
    assert body[0]["document_reference"] == "NF-888"
    assert body[0]["item_count"] == 1
    assert body[0]["total_quantity"] == 1
    assert body[1]["supplier_reference"] == "Fornecedor Reuso"
    assert body[1]["document_reference"] == "NF-777"
    assert body[1]["item_count"] == 2
    assert body[1]["total_quantity"] == 5


def test_receipts_endpoint_groups_entries_by_reference_set(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Receipts")
    variant_a, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    variant_b, _ = stock_factory(store_id=store.id, on_hand_qty=7)
    headers = auth_headers("manager@receipts.com", "secret123", "manager", store_id=store.id)

    response = client.post(
        "/inventory/entries",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Mestre",
            "document_reference": "DOC-900",
            "reason": "recebimento principal",
            "items": [
                {"variant_id": str(variant_a.id), "quantity": 2},
                {"variant_id": str(variant_b.id), "quantity": 4},
            ],
        },
    )
    assert response.status_code == 200

    list_response = client.get("/inventory/receipts", headers=headers)

    assert list_response.status_code == 200
    body = list_response.json()
    assert body["total"] == 1
    assert body["limit"] == 12
    assert body["offset"] == 0
    assert len(body["items"]) == 1
    assert body["items"][0]["supplier_reference"] == "Fornecedor Mestre"
    assert body["items"][0]["document_reference"] == "DOC-900"
    assert body["items"][0]["status"] == "posted"
    assert body["items"][0]["item_count"] == 2
    assert body["items"][0]["total_quantity"] == 6
    assert body["items"][0]["receipt_id"]


def test_receipt_detail_returns_grouped_items_for_selected_receipt(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Receipt Detail")
    variant_a, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    variant_b, _ = stock_factory(store_id=store.id, on_hand_qty=7)
    headers = auth_headers("manager@receipt-detail.com", "secret123", "manager", store_id=store.id)

    create_response = client.post(
        "/inventory/entries",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Detail",
            "document_reference": "DOC-901",
            "reason": "recebimento detalhado",
            "items": [
                {"variant_id": str(variant_a.id), "quantity": 1},
                {"variant_id": str(variant_b.id), "quantity": 5},
            ],
        },
    )
    assert create_response.status_code == 200

    list_response = client.get("/inventory/receipts", headers=headers)
    receipt_id = list_response.json()["items"][0]["receipt_id"]

    detail_response = client.get(f"/inventory/receipts/{receipt_id}", headers=headers)

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["supplier_reference"] == "Fornecedor Detail"
    assert detail["document_reference"] == "DOC-901"
    assert detail["status"] == "posted"
    assert detail["item_count"] == 2
    assert detail["total_quantity"] == 6
    assert len(detail["items"]) == 2


def test_receipt_export_csv_uses_stable_receipt_id(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Receipt Export")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    headers = auth_headers("manager@receipt-export.com", "secret123", "manager", store_id=store.id)

    create_response = client.post(
        "/inventory/entries",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Export",
            "document_reference": "DOC-999",
            "reason": "recebimento exportavel",
            "items": [{"variant_id": str(variant.id), "quantity": 2}],
        },
    )
    assert create_response.status_code == 200

    list_response = client.get("/inventory/receipts", headers=headers)
    receipt_id = list_response.json()["items"][0]["receipt_id"]

    export_response = client.get(f"/inventory/receipts/{receipt_id}/export", headers=headers)

    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("text/csv")
    assert receipt_id in export_response.text
    assert "Fornecedor Export" in export_response.text
    assert "DOC-999" in export_response.text


def test_receipts_endpoint_supports_limit_and_offset_pagination(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Receipts Paginada")
    headers = auth_headers("manager@receipts-page.com", "secret123", "manager", store_id=store.id)

    for index in range(3):
        variant, _ = stock_factory(store_id=store.id, on_hand_qty=10 + index)
        response = client.post(
            "/inventory/entries",
            headers=headers,
            json={
                "store_id": str(store.id),
                "supplier_reference": "Fornecedor Paginado",
                "document_reference": f"DOC-PAGE-{index}",
                "reason": "recebimento paginado",
                "items": [{"variant_id": str(variant.id), "quantity": 1}],
            },
        )
        assert response.status_code == 200

    list_response = client.get("/inventory/receipts?limit=2&offset=1", headers=headers)

    assert list_response.status_code == 200
    body = list_response.json()
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert len(body["items"]) == 2


def test_receipts_endpoint_can_filter_sensitive_drafts_with_pagination(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Draft Filter")
    headers = auth_headers("manager@draft-filter.com", "secret123", "manager", store_id=store.id)

    for index, quantity in enumerate([5, 25, 30]):
        variant, _ = stock_factory(store_id=store.id, on_hand_qty=20 + index)
        response = client.post(
            "/inventory/receipts/draft",
            headers=headers,
            json={
                "store_id": str(store.id),
                "supplier_reference": f"Fornecedor Draft {index}",
                "document_reference": f"DOC-DRAFT-{index}",
                "reason": "rascunho filtravel",
                "items": [{"variant_id": str(variant.id), "quantity": quantity}],
            },
        )
        assert response.status_code == 200

    list_response = client.get(
        "/inventory/receipts?status=draft&requires_approval=true&limit=1&offset=1",
        headers=headers,
    )

    assert list_response.status_code == 200
    body = list_response.json()
    assert body["total"] == 2
    assert body["limit"] == 1
    assert body["offset"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["requires_approval"] is True


def test_receipts_endpoint_q_search_matches_supplier_or_document(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Receipt Search")
    headers = auth_headers("manager@receipt-search.com", "secret123", "manager", store_id=store.id)

    variant_a, _ = stock_factory(store_id=store.id, on_hand_qty=10)
    variant_b, _ = stock_factory(store_id=store.id, on_hand_qty=12)

    first_response = client.post(
        "/inventory/entries",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Unico",
            "document_reference": "DOC-SEARCH-001",
            "reason": "recebimento para busca",
            "items": [{"variant_id": str(variant_a.id), "quantity": 1}],
        },
    )
    second_response = client.post(
        "/inventory/entries",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Outro Fornecedor",
            "document_reference": "DOC-SEARCH-XYZ",
            "reason": "recebimento para busca",
            "items": [{"variant_id": str(variant_b.id), "quantity": 1}],
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    supplier_response = client.get("/inventory/receipts?q=Unico", headers=headers)
    document_response = client.get("/inventory/receipts?q=XYZ", headers=headers)

    assert supplier_response.status_code == 200
    assert document_response.status_code == 200
    assert supplier_response.json()["total"] == 1
    assert supplier_response.json()["items"][0]["supplier_reference"] == "Fornecedor Unico"
    assert document_response.json()["total"] == 1
    assert document_response.json()["items"][0]["document_reference"] == "DOC-SEARCH-XYZ"


def test_receipt_status_can_be_updated_without_reversing_stock(
    client, db_session, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Receipt Status")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    headers = auth_headers("manager@receipt-status.com", "secret123", "manager", store_id=store.id)

    create_response = client.post(
        "/inventory/entries",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Status",
            "document_reference": "DOC-777",
            "reason": "recebimento para conferencia",
            "items": [{"variant_id": str(variant.id), "quantity": 2}],
        },
    )
    assert create_response.status_code == 200

    receipt_id = client.get("/inventory/receipts", headers=headers).json()["items"][0]["receipt_id"]
    status_response = client.post(
        f"/inventory/receipts/{receipt_id}/status",
        headers=headers,
        json={"status": "checked"},
    )

    assert status_response.status_code == 200
    body = status_response.json()
    assert body["status"] == "checked"

    db_session.expire_all()
    balance = (
        db_session.query(InventoryBalance)
        .filter(InventoryBalance.store_id == store.id, InventoryBalance.variant_id == variant.id)
        .one()
    )
    assert balance.on_hand_qty == 7


def test_receipt_cancel_reverses_stock_and_marks_document_canceled(
    client, db_session, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Receipt Cancel")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    headers = auth_headers("manager@receipt-cancel.com", "secret123", "manager", store_id=store.id)

    create_response = client.post(
        "/inventory/entries",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Cancel",
            "document_reference": "DOC-555",
            "reason": "recebimento cancelavel",
            "items": [{"variant_id": str(variant.id), "quantity": 3}],
        },
    )
    assert create_response.status_code == 200

    receipt_id = client.get("/inventory/receipts", headers=headers).json()["items"][0]["receipt_id"]
    cancel_response = client.post(f"/inventory/receipts/{receipt_id}/cancel", headers=headers)

    assert cancel_response.status_code == 200
    body = cancel_response.json()
    assert body["status"] == "canceled"

    db_session.expire_all()
    balance = (
        db_session.query(InventoryBalance)
        .filter(InventoryBalance.store_id == store.id, InventoryBalance.variant_id == variant.id)
        .one()
    )
    reversal = (
        db_session.query(StockMovement)
        .filter(
            StockMovement.store_id == store.id,
            StockMovement.variant_id == variant.id,
            StockMovement.reference_type == "receipt_cancel",
        )
        .one()
    )
    receipt = db_session.query(InventoryReceipt).filter(InventoryReceipt.id == uuid.UUID(receipt_id)).one()

    assert balance.on_hand_qty == 5
    assert reversal.quantity_delta == -3
    assert receipt.status == "canceled"


def test_receipt_rejects_invalid_status_transition_and_unknown_status(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Receipt Rules")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    headers = auth_headers("manager@receipt-rules.com", "secret123", "manager", store_id=store.id)

    create_response = client.post(
        "/inventory/entries",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Rules",
            "document_reference": "DOC-321",
            "reason": "recebimento com regras",
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
        },
    )
    assert create_response.status_code == 200

    receipt_id = client.get("/inventory/receipts", headers=headers).json()["items"][0]["receipt_id"]

    invalid_status_response = client.post(
        f"/inventory/receipts/{receipt_id}/status",
        headers=headers,
        json={"status": "draft"},
    )
    cancel_via_status_response = client.post(
        f"/inventory/receipts/{receipt_id}/status",
        headers=headers,
        json={"status": "canceled"},
    )

    assert invalid_status_response.status_code == 409
    assert cancel_via_status_response.status_code == 400


def test_canceled_receipt_cannot_change_status_again(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Receipt Frozen")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    headers = auth_headers("manager@receipt-frozen.com", "secret123", "manager", store_id=store.id)

    create_response = client.post(
        "/inventory/entries",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Freeze",
            "document_reference": "DOC-654",
            "reason": "recebimento congelado",
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
        },
    )
    assert create_response.status_code == 200

    receipt_id = client.get("/inventory/receipts", headers=headers).json()["items"][0]["receipt_id"]
    cancel_response = client.post(f"/inventory/receipts/{receipt_id}/cancel", headers=headers)
    assert cancel_response.status_code == 200

    status_response = client.post(
        f"/inventory/receipts/{receipt_id}/status",
        headers=headers,
        json={"status": "checked"},
    )

    assert status_response.status_code == 409


def test_receipt_draft_is_saved_without_changing_stock(
    client, db_session, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Draft")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    headers = auth_headers("operator@draft.com", "secret123", "operator", store_id=store.id)

    response = client.post(
        "/inventory/receipts/draft",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Draft",
            "document_reference": "DOC-DRAFT",
            "reason": "rascunho operacional",
            "items": [{"variant_id": str(variant.id), "quantity": 3}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "draft"
    assert body["item_count"] == 1
    assert body["total_quantity"] == 3

    db_session.expire_all()
    balance = (
        db_session.query(InventoryBalance)
        .filter(InventoryBalance.store_id == store.id, InventoryBalance.variant_id == variant.id)
        .one()
    )
    receipt = db_session.query(InventoryReceipt).filter(InventoryReceipt.id == uuid.UUID(body["receipt_id"])).one()
    items = db_session.query(InventoryReceiptItem).filter(InventoryReceiptItem.receipt_id == receipt.id).all()

    assert balance.on_hand_qty == 5
    assert receipt.status == "draft"
    assert len(items) == 1


def test_receipt_draft_can_be_posted_and_then_updates_stock(
    client, db_session, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Draft Post")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    headers = auth_headers("operator@draft-post.com", "secret123", "operator", store_id=store.id)

    draft_response = client.post(
        "/inventory/receipts/draft",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Draft Post",
            "document_reference": "DOC-POST",
            "reason": "draft para efetivar",
            "items": [{"variant_id": str(variant.id), "quantity": 2}],
        },
    )
    receipt_id = draft_response.json()["receipt_id"]

    post_response = client.post(f"/inventory/receipts/{receipt_id}/post", headers=headers)

    assert post_response.status_code == 200
    body = post_response.json()
    assert body["status"] == "posted"

    db_session.expire_all()
    balance = (
        db_session.query(InventoryBalance)
        .filter(InventoryBalance.store_id == store.id, InventoryBalance.variant_id == variant.id)
        .one()
    )
    movement = (
        db_session.query(StockMovement)
        .filter(StockMovement.receipt_group_id == uuid.UUID(receipt_id), StockMovement.movement_type == "entry")
        .one()
    )

    assert balance.on_hand_qty == 7
    assert movement.quantity_delta == 2


def test_receipt_draft_cannot_change_status_before_posting(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Draft Rule")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    headers = auth_headers("manager@draft-rule.com", "secret123", "manager", store_id=store.id)

    draft_response = client.post(
        "/inventory/receipts/draft",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Draft Rule",
            "document_reference": "DOC-RULE",
            "reason": "draft bloqueado",
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
        },
    )
    receipt_id = draft_response.json()["receipt_id"]

    status_response = client.post(
        f"/inventory/receipts/{receipt_id}/status",
        headers=headers,
        json={"status": "checked"},
    )

    assert status_response.status_code == 409


def test_receipt_draft_can_be_updated_before_posting(
    client, db_session, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Draft Update")
    variant_a, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    variant_b, _ = stock_factory(store_id=store.id, on_hand_qty=7)
    headers = auth_headers("manager@draft-update.com", "secret123", "manager", store_id=store.id)

    draft_response = client.post(
        "/inventory/receipts/draft",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Draft",
            "document_reference": "DOC-UPD-1",
            "reason": "primeira versao",
            "items": [{"variant_id": str(variant_a.id), "quantity": 1}],
        },
    )
    receipt_id = draft_response.json()["receipt_id"]

    update_response = client.put(
        f"/inventory/receipts/{receipt_id}/draft",
        headers=headers,
        json={
            "supplier_reference": "Fornecedor Revisado",
            "document_reference": "DOC-UPD-2",
            "reason": "segunda versao",
            "notes": "conferencia parcial atualizada",
            "items": [{"variant_id": str(variant_b.id), "quantity": 4}],
        },
    )

    assert update_response.status_code == 200
    body = update_response.json()
    assert body["status"] == "draft"
    assert body["supplier_reference"] == "Fornecedor Revisado"
    assert body["document_reference"] == "DOC-UPD-2"
    assert body["notes"] == "conferencia parcial atualizada"
    assert body["item_count"] == 1
    assert body["total_quantity"] == 4
    assert body["items"][0]["variant_id"] == str(variant_b.id)

    db_session.expire_all()
    receipt = db_session.query(InventoryReceipt).filter(InventoryReceipt.id == uuid.UUID(receipt_id)).one()
    items = db_session.query(InventoryReceiptItem).filter(InventoryReceiptItem.receipt_id == receipt.id).all()
    assert receipt.reason == "segunda versao"
    assert receipt.notes == "conferencia parcial atualizada"
    assert len(items) == 1
    assert items[0].variant_id == variant_b.id
    assert items[0].quantity == 4
    audit = (
        db_session.query(InventoryReceiptAuditLog)
        .filter(InventoryReceiptAuditLog.receipt_id == receipt.id)
        .order_by(InventoryReceiptAuditLog.created_at.asc())
        .all()
    )
    assert [entry.action for entry in audit] == ["draft_created", "draft_updated"]


def test_posted_receipt_cannot_be_updated_as_draft_anymore(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Draft Locked")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    headers = auth_headers("manager@draft-locked.com", "secret123", "manager", store_id=store.id)

    draft_response = client.post(
        "/inventory/receipts/draft",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Lock",
            "document_reference": "DOC-LOCK",
            "reason": "rascunho bloqueado",
            "items": [{"variant_id": str(variant.id), "quantity": 2}],
        },
    )
    receipt_id = draft_response.json()["receipt_id"]
    post_response = client.post(f"/inventory/receipts/{receipt_id}/post", headers=headers)
    assert post_response.status_code == 200

    update_response = client.put(
        f"/inventory/receipts/{receipt_id}/draft",
        headers=headers,
        json={
            "supplier_reference": "Fornecedor Novo",
            "document_reference": "DOC-NEW",
            "reason": "nao deveria editar",
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
        },
    )

    assert update_response.status_code == 409


def test_receipt_detail_exposes_notes_and_audit_entries(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Receipt Audit")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    headers = auth_headers("manager@receipt-audit.com", "secret123", "manager", store_id=store.id)

    draft_response = client.post(
        "/inventory/receipts/draft",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Audit",
            "document_reference": "DOC-AUDIT",
            "reason": "rascunho auditado",
            "notes": "aguardando conferencia final",
            "items": [{"variant_id": str(variant.id), "quantity": 2}],
        },
    )
    receipt_id = draft_response.json()["receipt_id"]

    detail_response = client.get(f"/inventory/receipts/{receipt_id}", headers=headers)

    assert detail_response.status_code == 200
    body = detail_response.json()
    assert body["notes"] == "aguardando conferencia final"
    assert len(body["audit"]) >= 1
    assert body["audit"][0]["action"] == "draft_created"


def test_receipts_report_groups_documents_by_status_and_supplier(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Report")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    headers = auth_headers("manager@report.com", "secret123", "manager", store_id=store.id)

    draft_response = client.post(
        "/inventory/receipts/draft",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Report",
            "document_reference": "DOC-REP-1",
            "reason": "rascunho relatorio",
            "items": [{"variant_id": str(variant.id), "quantity": 2}],
        },
    )
    receipt_id = draft_response.json()["receipt_id"]
    post_response = client.post(f"/inventory/receipts/{receipt_id}/post", headers=headers)
    assert post_response.status_code == 200

    second_draft = client.post(
        "/inventory/receipts/draft",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Report",
            "document_reference": "DOC-REP-2",
            "reason": "segundo rascunho",
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
        },
    )
    assert second_draft.status_code == 200

    report_response = client.get("/inventory/receipts-report", headers=headers)

    assert report_response.status_code == 200
    body = report_response.json()
    assert body["total"] >= 2
    assert body["limit"] == 12
    assert body["offset"] == 0
    assert len(body["items"]) >= 2
    assert any(item["status"] == "posted" and item["supplier_reference"] == "Fornecedor Report" and item["total_quantity"] == 2 for item in body["items"])
    assert any(item["status"] == "draft" and item["supplier_reference"] == "Fornecedor Report" and item["total_quantity"] == 1 for item in body["items"])


def test_receipts_report_can_be_exported_as_csv(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Report Export")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    headers = auth_headers("manager@report-export.com", "secret123", "manager", store_id=store.id)

    response = client.post(
        "/inventory/receipts/draft",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor CSV Report",
            "document_reference": "DOC-CSV-REP",
            "reason": "relatorio exportavel",
            "items": [{"variant_id": str(variant.id), "quantity": 2}],
        },
    )
    assert response.status_code == 200

    export_response = client.get("/inventory/receipts-report/export?sort_by=supplier&direction=asc", headers=headers)

    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("text/csv")
    assert "Fornecedor CSV Report" in export_response.text
    assert "draft" in export_response.text


def test_receipts_report_export_respects_q_for_supplier_and_document(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Report Export Search")
    headers = auth_headers("manager@report-export-search.com", "secret123", "manager", store_id=store.id)

    variant_a, _ = stock_factory(store_id=store.id, on_hand_qty=7)
    variant_b, _ = stock_factory(store_id=store.id, on_hand_qty=6)

    response_a = client.post(
        "/inventory/receipts/draft",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Exportavel",
            "document_reference": "DOC-EXP-001",
            "reason": "busca exportavel fornecedor",
            "items": [{"variant_id": str(variant_a.id), "quantity": 2}],
        },
    )
    response_b = client.post(
        "/inventory/receipts/draft",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Paralelo",
            "document_reference": "DOC-EXP-XYZ",
            "reason": "busca exportavel documento",
            "items": [{"variant_id": str(variant_b.id), "quantity": 1}],
        },
    )

    assert response_a.status_code == 200
    assert response_b.status_code == 200

    supplier_export = client.get(
        "/inventory/receipts-report/export?q=Exportavel&sort_by=supplier&direction=asc",
        headers=headers,
    )
    document_export = client.get(
        "/inventory/receipts-report/export?q=EXP-XYZ&sort_by=supplier&direction=asc",
        headers=headers,
    )

    assert supplier_export.status_code == 200
    assert supplier_export.headers["content-type"].startswith("text/csv")
    assert "Fornecedor Exportavel" in supplier_export.text
    assert "DOC-EXP-001" not in supplier_export.text
    assert "Fornecedor Paralelo" not in supplier_export.text

    assert document_export.status_code == 200
    assert document_export.headers["content-type"].startswith("text/csv")
    assert "Fornecedor Paralelo" in document_export.text
    assert "Fornecedor Exportavel" not in document_export.text


def test_receipts_report_q_search_matches_supplier_or_document(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Report Search")
    headers = auth_headers("manager@report-search.com", "secret123", "manager", store_id=store.id)

    variant_a, _ = stock_factory(store_id=store.id, on_hand_qty=8)
    variant_b, _ = stock_factory(store_id=store.id, on_hand_qty=9)

    supplier_response = client.post(
        "/inventory/receipts/draft",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Relatorio",
            "document_reference": "DOC-REL-001",
            "reason": "busca por fornecedor",
            "items": [{"variant_id": str(variant_a.id), "quantity": 2}],
        },
    )
    document_response = client.post(
        "/inventory/receipts/draft",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Outro fornecedor",
            "document_reference": "DOC-REL-XYZ",
            "reason": "busca por documento",
            "items": [{"variant_id": str(variant_b.id), "quantity": 1}],
        },
    )

    assert supplier_response.status_code == 200
    assert document_response.status_code == 200

    by_supplier = client.get("/inventory/receipts-report?q=Relatorio", headers=headers)
    by_document = client.get("/inventory/receipts-report?q=XYZ", headers=headers)

    assert by_supplier.status_code == 200
    assert by_document.status_code == 200
    assert len(by_supplier.json()["items"]) == 1
    assert by_supplier.json()["items"][0]["supplier_reference"] == "Fornecedor Relatorio"
    assert len(by_document.json()["items"]) == 1
    assert by_document.json()["items"][0]["supplier_reference"] == "Outro fornecedor"


def test_receipts_report_supports_limit_and_offset_pagination(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Report Paginado")
    headers = auth_headers("manager@report-page.com", "secret123", "manager", store_id=store.id)

    for index in range(3):
        variant, _ = stock_factory(store_id=store.id, on_hand_qty=10 + index)
        response = client.post(
            "/inventory/receipts/draft",
            headers=headers,
            json={
                "store_id": str(store.id),
                "supplier_reference": f"Fornecedor Page {index}",
                "document_reference": f"DOC-REPORT-{index}",
                "reason": "paginacao do relatorio",
                "items": [{"variant_id": str(variant.id), "quantity": 1}],
            },
        )
        assert response.status_code == 200

    report_response = client.get(
        "/inventory/receipts-report?sort_by=supplier&direction=asc&limit=2&offset=1",
        headers=headers,
    )

    assert report_response.status_code == 200
    body = report_response.json()
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert len(body["items"]) == 2


def test_receipts_report_exposes_pending_and_approved_sensitive_drafts(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Approval Report")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    manager_headers = auth_headers("manager@approval-report.com", "secret123", "manager", store_id=store.id)
    operator_headers = auth_headers("operator@approval-report.com", "secret123", "operator", store_id=store.id)

    pending_response = client.post(
        "/inventory/receipts/draft",
        headers=operator_headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Approval",
            "document_reference": "DOC-PENDING",
            "reason": "rascunho sensivel pendente",
            "items": [{"variant_id": str(variant.id), "quantity": 20}],
        },
    )
    assert pending_response.status_code == 200

    approved_response = client.post(
        "/inventory/receipts/draft",
        headers=operator_headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Approval",
            "document_reference": "DOC-APPROVED",
            "reason": "rascunho sensivel aprovado",
            "items": [{"variant_id": str(variant.id), "quantity": 21}],
        },
    )
    assert approved_response.status_code == 200

    approve_call = client.post(
        f"/inventory/receipts/{approved_response.json()['receipt_id']}/approve",
        headers=manager_headers,
    )
    assert approve_call.status_code == 200

    report_response = client.get("/inventory/receipts-report?sort_by=approval&direction=desc", headers=manager_headers)

    assert report_response.status_code == 200
    body = report_response.json()
    sensitive_entry = next(
        item for item in body["items"]
        if item["status"] == "draft" and item["supplier_reference"] == "Fornecedor Approval" and item["requires_approval"]
    )
    assert sensitive_entry["pending_approval_receipts"] == 1
    assert sensitive_entry["approved_receipts"] == 1
    assert sensitive_entry["receipts"] == 2


def test_post_receipt_records_bulk_confirmation_audit(
    client, db_session, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Bulk Audit")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    headers = auth_headers("manager@bulk-audit.com", "secret123", "manager", store_id=store.id)

    draft_response = client.post(
        "/inventory/receipts/draft",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Bulk",
            "document_reference": "DOC-BULK",
            "reason": "rascunho com confirmacao bulk",
            "items": [{"variant_id": str(variant.id), "quantity": 2}],
        },
    )
    receipt_id = draft_response.json()["receipt_id"]

    post_response = client.post(
        f"/inventory/receipts/{receipt_id}/post",
        headers={**headers, "X-Receipt-Bulk-Confirmed": "confirmed_via_bulk_action"},
    )

    assert post_response.status_code == 200
    actions = [
        entry.action
        for entry in db_session.query(InventoryReceiptAuditLog)
        .filter(InventoryReceiptAuditLog.receipt_id == uuid.UUID(receipt_id))
        .order_by(InventoryReceiptAuditLog.created_at.asc())
        .all()
    ]
    assert "bulk_post_confirmed" in actions
    assert "draft_posted" in actions


def test_supplier_risk_target_and_snapshot_are_persisted(
    client, db_session, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Supplier Snapshot")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    headers = auth_headers("manager@snapshot.com", "secret123", "manager", store_id=store.id)

    target_response = client.put(
        "/inventory/supplier-risk-targets",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Snapshot",
            "target_hours": 36,
        },
    )
    assert target_response.status_code == 200

    draft_response = client.post(
        "/inventory/receipts/draft",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Snapshot",
            "document_reference": "DOC-SNAP",
            "reason": "rascunho para snapshot",
            "items": [{"variant_id": str(variant.id), "quantity": 20}],
        },
    )
    assert draft_response.status_code == 200

    report_response = client.get("/inventory/receipts-report", headers=headers)
    assert report_response.status_code == 200
    entry = next(
        item for item in report_response.json()["items"]
        if item["supplier_reference"] == "Fornecedor Snapshot" and item["requires_approval"]
    )
    assert entry["supplier_target_hours"] == 36

    target = (
        db_session.query(InventorySupplierRiskTarget)
        .filter(InventorySupplierRiskTarget.store_id == store.id)
        .one()
    )
    snapshot = (
        db_session.query(InventorySupplierRiskSnapshot)
        .filter(
            InventorySupplierRiskSnapshot.store_id == store.id,
            InventorySupplierRiskSnapshot.supplier_reference == "Fornecedor Snapshot",
        )
        .one()
    )
    assert target.target_hours == 36
    assert snapshot.target_hours == 36
    assert snapshot.open_critical_count >= 1


def test_supplier_risk_history_can_be_exported_as_csv(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Risk Export")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    headers = auth_headers("manager@risk-export.com", "secret123", "manager", store_id=store.id)

    client.put(
        "/inventory/supplier-risk-targets",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Risk Export",
            "target_hours": 30,
        },
    )
    client.post(
        "/inventory/receipts/draft",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Risk Export",
            "document_reference": "DOC-RISK-EXPORT",
            "reason": "rascunho para exportar historico",
            "items": [{"variant_id": str(variant.id), "quantity": 20}],
        },
    )
    report_response = client.get("/inventory/receipts-report", headers=headers)
    assert report_response.status_code == 200

    export_response = client.get("/inventory/supplier-risk-history/export", headers=headers)

    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("text/csv")
    assert "Fornecedor Risk Export" in export_response.text


def test_operator_cannot_edit_other_users_draft(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Draft Access")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    manager_headers = auth_headers("manager@draft-access.com", "secret123", "manager", store_id=store.id)
    operator_headers = auth_headers("operator@draft-access.com", "secret123", "operator", store_id=store.id)

    draft_response = client.post(
        "/inventory/receipts/draft",
        headers=manager_headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Protegido",
            "document_reference": "DOC-LOCKED",
            "reason": "rascunho protegido",
            "items": [{"variant_id": str(variant.id), "quantity": 1}],
        },
    )
    receipt_id = draft_response.json()["receipt_id"]

    update_response = client.put(
        f"/inventory/receipts/{receipt_id}/draft",
        headers=operator_headers,
        json={
          "supplier_reference": "Fornecedor Invalido",
          "document_reference": "DOC-INVALID",
          "reason": "tentativa sem permissao",
          "items": [{"variant_id": str(variant.id), "quantity": 2}],
        },
    )

    assert update_response.status_code == 403


def test_receipt_draft_can_be_discarded_without_stock_effect(
    client, db_session, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Draft Discard")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    headers = auth_headers("manager@draft-discard.com", "secret123", "manager", store_id=store.id)

    draft_response = client.post(
        "/inventory/receipts/draft",
        headers=headers,
        json={
            "store_id": str(store.id),
            "supplier_reference": "Fornecedor Discard",
            "document_reference": "DOC-DISCARD",
            "reason": "rascunho para descartar",
            "items": [{"variant_id": str(variant.id), "quantity": 2}],
        },
    )
    receipt_id = draft_response.json()["receipt_id"]

    discard_response = client.delete(f"/inventory/receipts/{receipt_id}/draft", headers=headers)

    assert discard_response.status_code == 200
    db_session.expire_all()
    balance = (
        db_session.query(InventoryBalance)
        .filter(InventoryBalance.store_id == store.id, InventoryBalance.variant_id == variant.id)
        .one()
    )
    receipt = db_session.query(InventoryReceipt).filter(InventoryReceipt.id == uuid.UUID(receipt_id)).first()
    items = db_session.query(InventoryReceiptItem).filter(InventoryReceiptItem.receipt_id == uuid.UUID(receipt_id)).all()

    assert balance.on_hand_qty == 5
    assert receipt is None
    assert items == []


def test_partial_return_restores_only_returned_quantity(client, db_session, auth_headers, store_factory, stock_factory):
    store = store_factory("Loja Retorno")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=10)
    headers = auth_headers("manager@retorno.com", "secret123", "manager", store_id=store.id)

    sale_response = client.post(
        "/sales/",
        headers=headers,
        json={
            "store_id": str(store.id),
            "items": [
                {
                    "variant_id": str(variant.id),
                    "quantity": 4,
                    "unit_price": "20.00",
                }
            ],
        },
    )

    assert sale_response.status_code == 200
    sale_id = sale_response.json()["id"]

    return_response = client.post(
        f"/sales/{sale_id}/return",
        headers=headers,
        json={
            "items": [
                {
                    "variant_id": str(variant.id),
                    "quantity": 2,
                }
            ]
        },
    )

    assert return_response.status_code == 200
    db_session.expire_all()

    balance = (
        db_session.query(InventoryBalance)
        .filter(InventoryBalance.store_id == store.id, InventoryBalance.variant_id == variant.id)
        .one()
    )
    movements = (
        db_session.query(StockMovement)
        .filter(
            StockMovement.store_id == store.id,
            StockMovement.variant_id == variant.id,
            StockMovement.reference_type == "sale_return",
        )
        .all()
    )

    assert balance.on_hand_qty == 8
    assert len(movements) == 1
    assert movements[0].movement_type == "return"
    assert movements[0].quantity_delta == 2


def test_partial_return_cannot_exceed_sold_quantity_minus_previous_returns(client, auth_headers, store_factory, stock_factory):
    store = store_factory("Loja Limite")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=8)
    headers = auth_headers("manager@limite.com", "secret123", "manager", store_id=store.id)

    sale_response = client.post(
        "/sales/",
        headers=headers,
        json={
            "store_id": str(store.id),
            "items": [
                {
                    "variant_id": str(variant.id),
                    "quantity": 3,
                    "unit_price": "20.00",
                }
            ],
        },
    )

    sale_id = sale_response.json()["id"]
    first_return = client.post(
        f"/sales/{sale_id}/return",
        headers=headers,
        json={"items": [{"variant_id": str(variant.id), "quantity": 2}]},
    )
    assert first_return.status_code == 200

    second_return = client.post(
        f"/sales/{sale_id}/return",
        headers=headers,
        json={"items": [{"variant_id": str(variant.id), "quantity": 2}]},
    )

    assert second_return.status_code == 409


def test_dashboard_returns_consolidated_sales_and_inventory_metrics(
    client, db_session, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Dashboard")
    variant_a, _ = stock_factory(store_id=store.id, on_hand_qty=5)
    variant_b, balance_b = stock_factory(store_id=store.id, on_hand_qty=1)
    balance_b.reserved_qty = 2
    db_session.commit()
    admin_headers = auth_headers("admin@rede.com", "secret123", "admin")

    first_sale = client.post(
        "/sales/",
        headers=admin_headers,
        json={
            "store_id": str(store.id),
            "discount_amount": "5.00",
            "items": [
                {
                    "variant_id": str(variant_a.id),
                    "quantity": 2,
                    "unit_price": "20.00",
                },
                {
                    "variant_id": str(variant_b.id),
                    "quantity": 1,
                    "unit_price": "15.00",
                },
            ],
        },
    )
    assert first_sale.status_code == 200

    second_sale = client.post(
        "/sales/",
        headers=admin_headers,
        json={
            "store_id": str(store.id),
            "items": [
                {
                    "variant_id": str(variant_a.id),
                    "quantity": 1,
                    "unit_price": "20.00",
                }
            ],
        },
    )
    assert second_sale.status_code == 200

    cancel_response = client.post(
        f"/sales/{second_sale.json()['id']}/cancel",
        headers=admin_headers,
    )
    assert cancel_response.status_code == 200

    response = client.get(
        f"/dashboard/?store_id={store.id}&low_stock_threshold=2",
        headers=admin_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["scope_store_id"] == str(store.id)
    assert body["sales"]["completed_count"] == 1
    assert body["sales"]["canceled_count"] == 1
    assert body["sales"]["gross_revenue"] == "55.00"
    assert body["sales"]["discount_total"] == "5.00"
    assert body["sales"]["net_revenue"] == "50.00"
    assert body["sales"]["items_sold"] == 3
    assert body["inventory"]["tracked_variants"] == 2
    assert body["inventory"]["total_on_hand_qty"] == 3
    assert body["inventory"]["total_reserved_qty"] == 2
    assert body["inventory"]["low_stock_variants"] == 0
    assert body["inventory"]["out_of_stock_variants"] == 1
    assert body["stores"] == [
        {
            "store_id": str(store.id),
            "sales_count": 1,
            "net_revenue": "50.00",
            "on_hand_qty": 3,
        }
    ]
    assert len(body["daily_sales"]) == 7
    assert body["daily_sales"][-1]["sales_count"] == 1
    assert body["daily_sales"][-1]["net_revenue"] == "50.00"
    assert body["top_variants"] == [
        {
            "variant_id": str(variant_a.id),
            "sku": variant_a.sku,
            "product_name": variant_a.product.name,
            "quantity_sold": 2,
            "net_revenue": "40.00",
        },
        {
            "variant_id": str(variant_b.id),
            "sku": variant_b.sku,
            "product_name": variant_b.product.name,
            "quantity_sold": 1,
            "net_revenue": "15.00",
        },
    ]


def test_dashboard_respects_non_admin_store_scope(
    client, auth_headers, store_factory, stock_factory
):
    store_a = store_factory("Loja A")
    store_b = store_factory("Loja B")
    variant_a, _ = stock_factory(store_id=store_a.id, on_hand_qty=4)
    variant_b, _ = stock_factory(store_id=store_b.id, on_hand_qty=9)
    admin_headers = auth_headers("admin@rede.com", "secret123", "admin")
    manager_headers = auth_headers(
        "manager@loja-a.com",
        "secret123",
        "manager",
        store_id=store_a.id,
    )

    sale_a = client.post(
        "/sales/",
        headers=admin_headers,
        json={
            "store_id": str(store_a.id),
            "items": [
                {
                    "variant_id": str(variant_a.id),
                    "quantity": 1,
                    "unit_price": "12.00",
                }
            ],
        },
    )
    sale_b = client.post(
        "/sales/",
        headers=admin_headers,
        json={
            "store_id": str(store_b.id),
            "items": [
                {
                    "variant_id": str(variant_b.id),
                    "quantity": 2,
                    "unit_price": "10.00",
                }
            ],
        },
    )

    assert sale_a.status_code == 200
    assert sale_b.status_code == 200

    own_scope_response = client.get("/dashboard/", headers=manager_headers)
    forbidden_response = client.get(
        f"/dashboard/?store_id={store_b.id}",
        headers=manager_headers,
    )

    assert own_scope_response.status_code == 200
    own_scope_body = own_scope_response.json()
    assert own_scope_body["scope_store_id"] == str(store_a.id)
    assert own_scope_body["sales"]["completed_count"] == 1
    assert own_scope_body["sales"]["net_revenue"] == "12.00"
    assert own_scope_body["inventory"]["total_on_hand_qty"] == 3
    assert own_scope_body["stores"] == [
        {
            "store_id": str(store_a.id),
            "sales_count": 1,
            "net_revenue": "12.00",
            "on_hand_qty": 3,
        }
    ]
    assert forbidden_response.status_code == 403


def test_dashboard_daily_sales_and_top_variants_consider_date_window(
    client, db_session, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Janela")
    variant_a, _ = stock_factory(store_id=store.id, on_hand_qty=20)
    variant_b, _ = stock_factory(store_id=store.id, on_hand_qty=20)
    admin_headers = auth_headers("admin@rede.com", "secret123", "admin")

    sale_old = client.post(
        "/sales/",
        headers=admin_headers,
        json={
            "store_id": str(store.id),
            "items": [
                {
                    "variant_id": str(variant_a.id),
                    "quantity": 4,
                    "unit_price": "10.00",
                }
            ],
        },
    )
    sale_recent = client.post(
        "/sales/",
        headers=admin_headers,
        json={
            "store_id": str(store.id),
            "items": [
                {
                    "variant_id": str(variant_b.id),
                    "quantity": 2,
                    "unit_price": "12.00",
                },
                {
                    "variant_id": str(variant_a.id),
                    "quantity": 1,
                    "unit_price": "10.00",
                },
            ],
        },
    )

    assert sale_old.status_code == 200
    assert sale_recent.status_code == 200

    db_session.query(Sale).filter(Sale.id == uuid.UUID(sale_old.json()["id"])).update(
        {"sold_at": datetime.now(timezone.utc) - timedelta(days=10)}
    )
    db_session.query(Sale).filter(Sale.id == uuid.UUID(sale_recent.json()["id"])).update(
        {"sold_at": datetime.now(timezone.utc) - timedelta(days=1)}
    )
    db_session.commit()

    response = client.get(
        f"/dashboard/?store_id={store.id}&days=3&top_limit=1",
        headers=admin_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["daily_sales"]) == 3
    assert body["daily_sales"][-2]["sales_count"] == 1
    assert body["daily_sales"][-2]["net_revenue"] == "34.00"
    assert body["daily_sales"][-1]["sales_count"] == 0
    assert body["top_variants"] == [
        {
            "variant_id": str(variant_b.id),
            "sku": variant_b.sku,
            "product_name": variant_b.product.name,
            "quantity_sold": 2,
            "net_revenue": "24.00",
        }
    ]


def test_sale_is_blocked_for_another_store_scope(client, auth_headers, store_factory, stock_factory):
    store_a = store_factory("Loja A")
    store_b = store_factory("Loja B")
    variant, _ = stock_factory(store_id=store_b.id, on_hand_qty=10)
    headers = auth_headers(
        "operator@loja-a.com",
        "secret123",
        "operator",
        store_id=store_a.id,
    )

    response = client.post(
        "/sales/",
        headers=headers,
        json={
            "store_id": str(store_b.id),
            "items": [
                {
                    "variant_id": str(variant.id),
                    "quantity": 1,
                    "unit_price": "20.00",
                }
            ],
        },
    )

    assert response.status_code == 403


def test_transfer_moves_stock_between_stores_and_creates_movements(
    client, db_session, auth_headers, store_factory, stock_factory
):
    source_store = store_factory("Loja Origem")
    destination_store = store_factory("Loja Destino")
    variant, _ = stock_factory(store_id=source_store.id, on_hand_qty=10)
    headers = auth_headers(
        "admin@rede.com",
        "secret123",
        "admin",
    )

    response = client.post(
        "/inventory/transfer",
        headers=headers,
        json={
            "source_store_id": str(source_store.id),
            "destination_store_id": str(destination_store.id),
            "variant_id": str(variant.id),
            "quantity": 4,
            "reason": "reposicao entre lojas",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_balance"]["on_hand_qty"] == 6
    assert body["destination_balance"]["on_hand_qty"] == 4

    db_session.expire_all()
    source_balance = (
        db_session.query(InventoryBalance)
        .filter(
            InventoryBalance.store_id == source_store.id,
            InventoryBalance.variant_id == variant.id,
        )
        .one()
    )
    destination_balance = (
        db_session.query(InventoryBalance)
        .filter(
            InventoryBalance.store_id == destination_store.id,
            InventoryBalance.variant_id == variant.id,
        )
        .one()
    )
    movements = (
        db_session.query(StockMovement)
        .filter(StockMovement.variant_id == variant.id)
        .order_by(StockMovement.created_at.asc())
        .all()
    )

    assert source_balance.on_hand_qty == 6
    assert destination_balance.on_hand_qty == 4
    assert len(movements) == 2
    assert movements[0].movement_type == "transfer_out"
    assert movements[0].quantity_delta == -4
    assert movements[0].reference_id == destination_store.id
    assert movements[1].movement_type == "transfer_in"
    assert movements[1].quantity_delta == 4
    assert movements[1].reference_id == source_store.id


def test_transfer_is_blocked_when_user_has_no_access_to_destination_store(
    client, auth_headers, store_factory, stock_factory
):
    source_store = store_factory("Loja A")
    destination_store = store_factory("Loja B")
    variant, _ = stock_factory(store_id=source_store.id, on_hand_qty=10)
    headers = auth_headers(
        "manager@loja-a.com",
        "secret123",
        "manager",
        store_id=source_store.id,
    )

    response = client.post(
        "/inventory/transfer",
        headers=headers,
        json={
            "source_store_id": str(source_store.id),
            "destination_store_id": str(destination_store.id),
            "variant_id": str(variant.id),
            "quantity": 2,
            "reason": "sem acesso",
        },
    )

    assert response.status_code == 403


def test_movements_can_be_filtered_by_store_variant_and_type(
    client, auth_headers, store_factory, stock_factory
):
    store_a = store_factory("Loja A")
    store_b = store_factory("Loja B")
    variant_a, _ = stock_factory(store_id=store_a.id, on_hand_qty=10)
    variant_b, _ = stock_factory(store_id=store_b.id, on_hand_qty=10)
    admin_headers = auth_headers("admin@rede.com", "secret123", "admin")

    transfer_response = client.post(
        "/inventory/transfer",
        headers=admin_headers,
        json={
            "source_store_id": str(store_a.id),
            "destination_store_id": str(store_b.id),
            "variant_id": str(variant_a.id),
            "quantity": 3,
            "reason": "ajuste logistico",
        },
    )

    assert transfer_response.status_code == 200

    filtered_response = client.get(
        f"/inventory/movements?store_id={store_a.id}&variant_id={variant_a.id}&movement_type=transfer_out",
        headers=admin_headers,
    )

    assert filtered_response.status_code == 200
    body = filtered_response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["store_id"] == str(store_a.id)
    assert body["items"][0]["variant_id"] == str(variant_a.id)
    assert body["items"][0]["movement_type"] == "transfer_out"

    other_variant_response = client.get(
        f"/inventory/movements?variant_id={variant_b.id}",
        headers=admin_headers,
    )

    assert other_variant_response.status_code == 200
    assert other_variant_response.json()["items"] == []


def test_movements_filter_respects_store_scope_for_non_admin(
    client, auth_headers, store_factory, stock_factory
):
    store_a = store_factory("Loja A")
    store_b = store_factory("Loja B")
    variant, _ = stock_factory(store_id=store_a.id, on_hand_qty=10)
    admin_headers = auth_headers("admin@rede.com", "secret123", "admin")
    manager_headers = auth_headers(
        "manager@loja-a.com",
        "secret123",
        "manager",
        store_id=store_a.id,
    )

    response = client.post(
        "/inventory/transfer",
        headers=admin_headers,
        json={
            "source_store_id": str(store_a.id),
            "destination_store_id": str(store_b.id),
            "variant_id": str(variant.id),
            "quantity": 2,
            "reason": "teste escopo",
        },
    )

    assert response.status_code == 200

    forbidden_response = client.get(
        f"/inventory/movements?store_id={store_b.id}",
        headers=manager_headers,
    )

    assert forbidden_response.status_code == 403
