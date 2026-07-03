from app.models.inventory import InventoryBalance


def test_create_count_add_item_and_close_updates_stock(
    client,
    db_session,
    auth_headers,
    store_factory,
    stock_factory,
):
    store = store_factory("Loja Inventario")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=8)
    headers = auth_headers(
        "manager@inventario.com",
        "secret123",
        "manager",
        store_id=store.id,
    )

    create_response = client.post(
        "/counts/",
        headers=headers,
        json={"store_id": str(store.id), "scope": "cycle", "reason": "contagem semanal"},
    )

    assert create_response.status_code == 200
    count_id = create_response.json()["id"]

    item_response = client.post(
        f"/counts/{count_id}/items",
        headers=headers,
        json={"variant_id": str(variant.id), "counted_quantity": 5},
    )

    assert item_response.status_code == 200
    assert item_response.json()["items"][0]["difference_quantity"] == -3

    close_response = client.post(f"/counts/{count_id}/close", headers=headers)

    assert close_response.status_code == 200
    assert close_response.json()["status"] == "closed"

    db_session.expire_all()
    balance = (
        db_session.query(InventoryBalance)
        .filter(InventoryBalance.store_id == store.id, InventoryBalance.variant_id == variant.id)
        .one()
    )
    assert balance.on_hand_qty == 5


def test_operator_cannot_create_inventory_count(client, auth_headers, store_factory):
    store = store_factory("Loja Restrita")
    headers = auth_headers(
        "operator@inventario.com",
        "secret123",
        "operator",
        store_id=store.id,
    )

    response = client.post(
        "/counts/",
        headers=headers,
        json={"store_id": str(store.id), "scope": "cycle"},
    )

    assert response.status_code == 403


def test_admin_can_filter_counts_by_store(client, auth_headers, store_factory):
    store_a = store_factory("Loja A")
    store_b = store_factory("Loja B")
    admin_headers = auth_headers("admin@rede.com", "secret123", "admin")

    create_a = client.post(
        "/counts/",
        headers=admin_headers,
        json={"store_id": str(store_a.id), "scope": "cycle"},
    )
    create_b = client.post(
        "/counts/",
        headers=admin_headers,
        json={"store_id": str(store_b.id), "scope": "full"},
    )

    assert create_a.status_code == 200
    assert create_b.status_code == 200

    filtered = client.get(f"/counts/?store_id={store_b.id}", headers=admin_headers)

    assert filtered.status_code == 200
    body = filtered.json()
    assert len(body) == 1
    assert body[0]["store_id"] == str(store_b.id)
