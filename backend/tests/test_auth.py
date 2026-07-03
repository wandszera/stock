def test_bootstrap_admin_only_once(client):
    payload = {
        "name": "Admin",
        "email": "admin@example.com",
        "password": "secret123",
    }

    first_response = client.post("/auth/bootstrap", json=payload)
    second_response = client.post("/auth/bootstrap", json=payload)

    assert first_response.status_code == 201
    assert first_response.json()["user"]["role"] == "admin"
    assert second_response.status_code == 409


def test_login_and_me_returns_authenticated_user(client, user_factory):
    user_factory(
        email="manager@example.com",
        password="secret123",
        role="manager",
    )

    login_response = client.post(
        "/auth/login",
        data={"username": "manager@example.com", "password": "secret123"},
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["email"] == "manager@example.com"
    assert me_response.json()["role"] == "manager"
