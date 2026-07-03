def test_admin_can_create_list_get_and_update_store(client, auth_headers):
    admin_headers = auth_headers("admin@stores.com", "secret123", "admin")

    create_response = client.post(
        "/stores/",
        headers=admin_headers,
        json={
            "name": "Loja Centro",
            "timezone": "America/Sao_Paulo",
            "is_active": True,
        },
    )

    assert create_response.status_code == 200
    store_id = create_response.json()["id"]

    list_response = client.get("/stores/", headers=admin_headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    get_response = client.get(f"/stores/{store_id}", headers=admin_headers)
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Loja Centro"

    update_response = client.patch(
        f"/stores/{store_id}",
        headers=admin_headers,
        json={"name": "Loja Centro Norte", "is_active": False},
    )

    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Loja Centro Norte"
    assert update_response.json()["is_active"] is False


def test_non_admin_only_sees_and_accesses_own_store(client, auth_headers, store_factory):
    store_a = store_factory("Loja A")
    store_b = store_factory("Loja B")
    headers = auth_headers(
        "manager@loja-a.com",
        "secret123",
        "manager",
        store_id=store_a.id,
    )

    list_response = client.get("/stores/", headers=headers)
    assert list_response.status_code == 200
    body = list_response.json()
    assert len(body) == 1
    assert body[0]["id"] == str(store_a.id)

    own_store_response = client.get(f"/stores/{store_a.id}", headers=headers)
    assert own_store_response.status_code == 200

    other_store_response = client.get(f"/stores/{store_b.id}", headers=headers)
    assert other_store_response.status_code == 403


def test_non_admin_cannot_create_or_update_store(client, auth_headers, store_factory):
    store = store_factory("Loja Restrita")
    headers = auth_headers(
        "operator@loja.com",
        "secret123",
        "operator",
        store_id=store.id,
    )

    create_response = client.post(
        "/stores/",
        headers=headers,
        json={"name": "Nova Loja"},
    )
    update_response = client.patch(
        f"/stores/{store.id}",
        headers=headers,
        json={"name": "Nome Alterado"},
    )

    assert create_response.status_code == 403
    assert update_response.status_code == 403
