from app.models.audit import AuditEvent
from app.models.inventory import StockMovement


def test_sale_creates_correlated_audit_event_and_stock_movement(
    client, db_session, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Auditoria")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=10)
    headers = auth_headers("manager@audit.com", "secret123", "manager", store_id=store.id)
    headers["X-Request-ID"] = "sale-audit-001"

    response = client.post(
        "/sales/",
        headers=headers,
        json={
            "store_id": str(store.id),
            "items": [{"variant_id": str(variant.id), "quantity": 2, "unit_price": "25.00"}],
        },
    )

    assert response.status_code == 200
    db_session.expire_all()
    event = db_session.query(AuditEvent).one()
    movement = db_session.query(StockMovement).one()
    assert event.action == "sale.created"
    assert str(event.entity_id) == response.json()["id"]
    assert event.request_id == "sale-audit-001"
    assert event.event_metadata["total_quantity"] == 2
    assert movement.request_id == event.request_id


def test_admin_can_query_audit_events_with_actor_and_movements(
    client, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Consulta Auditoria")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=10)
    admin_headers = auth_headers("admin@audit.com", "secret123", "admin")
    admin_headers["X-Request-ID"] = "trace-query-001"
    sale_response = client.post(
        "/sales/",
        headers=admin_headers,
        json={
            "store_id": str(store.id),
            "items": [{"variant_id": str(variant.id), "quantity": 1, "unit_price": "20.00"}],
        },
    )

    response = client.get(
        "/audit/events?request_id=trace-query-001",
        headers=admin_headers,
    )

    assert sale_response.status_code == 200
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["actor_email"] == "admin@audit.com"
    assert body["items"][0]["request_id"] == "trace-query-001"
    assert len(body["items"][0]["movement_ids"]) == 1


def test_manager_audit_query_is_restricted_to_own_store(
    client, auth_headers, store_factory, stock_factory
):
    own_store = store_factory("Loja Propria Auditoria")
    other_store = store_factory("Outra Loja Auditoria")
    variant, _ = stock_factory(store_id=other_store.id, on_hand_qty=10)
    admin_headers = auth_headers("admin@scope-audit.com", "secret123", "admin")
    manager_headers = auth_headers(
        "manager@scope-audit.com", "secret123", "manager", store_id=own_store.id
    )
    client.post(
        "/sales/",
        headers=admin_headers,
        json={
            "store_id": str(other_store.id),
            "items": [{"variant_id": str(variant.id), "quantity": 1, "unit_price": "20.00"}],
        },
    )

    own_scope = client.get("/audit/events", headers=manager_headers)
    forbidden_scope = client.get(
        f"/audit/events?store_id={other_store.id}", headers=manager_headers
    )

    assert own_scope.status_code == 200
    assert own_scope.json()["items"] == []
    assert forbidden_scope.status_code == 403


def test_operator_cannot_query_unified_audit_trail(
    client, auth_headers, store_factory
):
    store = store_factory("Loja Operador Auditoria")
    headers = auth_headers(
        "operator@audit.com", "secret123", "operator", store_id=store.id
    )

    response = client.get("/audit/events", headers=headers)

    assert response.status_code == 403
