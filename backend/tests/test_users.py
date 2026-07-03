def test_admin_can_create_list_get_and_update_user(client, auth_headers, store_factory):
    store = store_factory("Loja Centro")
    admin_headers = auth_headers("admin@users.com", "secret123", "admin")

    create_response = client.post(
        "/users/",
        headers=admin_headers,
        json={
            "name": "Maria Operadora",
            "email": "maria@empresa.com",
            "password": "secret123",
            "role": "operator",
            "store_id": str(store.id),
            "is_active": True,
        },
    )

    assert create_response.status_code == 200
    user_id = create_response.json()["id"]

    list_response = client.get("/users/", headers=admin_headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 2

    get_response = client.get(f"/users/{user_id}", headers=admin_headers)
    assert get_response.status_code == 200
    assert get_response.json()["email"] == "maria@empresa.com"

    update_response = client.patch(
        f"/users/{user_id}",
        headers=admin_headers,
        json={"name": "Maria Gestora", "role": "manager", "is_active": False},
    )

    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Maria Gestora"
    assert update_response.json()["role"] == "manager"
    assert update_response.json()["is_active"] is False


def test_non_admin_only_sees_and_accesses_users_from_same_store(
    client, user_factory, auth_headers, store_factory
):
    store_a = store_factory("Loja A")
    store_b = store_factory("Loja B")
    same_store_user = user_factory(
        email="operador-a@empresa.com",
        password="secret123",
        role="operator",
        store_id=store_a.id,
    )
    other_store_user = user_factory(
        email="operador-b@empresa.com",
        password="secret123",
        role="operator",
        store_id=store_b.id,
    )
    manager_headers = auth_headers(
        "manager@loja-a.com",
        "secret123",
        "manager",
        store_id=store_a.id,
    )

    list_response = client.get("/users/", headers=manager_headers)
    assert list_response.status_code == 200
    listed_emails = {item["email"] for item in list_response.json()}
    assert "operador-a@empresa.com" in listed_emails
    assert "operador-b@empresa.com" not in listed_emails

    own_store_response = client.get(f"/users/{same_store_user.id}", headers=manager_headers)
    assert own_store_response.status_code == 200

    other_store_response = client.get(f"/users/{other_store_user.id}", headers=manager_headers)
    assert other_store_response.status_code == 403


def test_manager_can_update_same_store_user_but_not_role_or_store(
    client, db_session, user_factory, auth_headers, store_factory
):
    store_a = store_factory("Loja A")
    store_b = store_factory("Loja B")
    target_user = user_factory(
        email="operador@empresa.com",
        password="secret123",
        role="operator",
        store_id=store_a.id,
    )
    manager_headers = auth_headers(
        "manager@loja-a.com",
        "secret123",
        "manager",
        store_id=store_a.id,
    )

    response = client.patch(
        f"/users/{target_user.id}",
        headers=manager_headers,
        json={
            "name": "Operador Atualizado",
            "role": "admin",
            "store_id": str(store_b.id),
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Operador Atualizado"
    assert response.json()["role"] == "operator"
    assert response.json()["store_id"] == str(store_a.id)

    db_session.expire_all()


def test_non_admin_cannot_create_user(client, auth_headers, store_factory):
    store = store_factory("Loja Restrita")
    headers = auth_headers(
        "operator@loja.com",
        "secret123",
        "operator",
        store_id=store.id,
    )

    response = client.post(
        "/users/",
        headers=headers,
        json={
            "name": "Novo Usuario",
            "email": "novo@empresa.com",
            "password": "secret123",
            "role": "operator",
            "store_id": str(store.id),
        },
    )

    assert response.status_code == 403
