from app.models import User


def register(client, **overrides):
    payload = {"name": "Carol", "email": "carol@example.com", "password": "password123"}
    payload.update(overrides)
    return client.post("/auth/register", json=payload)


def test_register_creates_customer(client):
    assert register(client).status_code == 201
    assert User.query.filter_by(email="carol@example.com").one().role == "customer"


def test_register_ignores_role_in_payload(client):
    register(client, role="admin")
    assert User.query.filter_by(email="carol@example.com").one().role == "customer"


def test_register_duplicate_email_is_409(client):
    assert register(client, email="alice@example.com").status_code == 409


def test_register_rejects_short_password(client):
    assert register(client, password="123").status_code == 400


def test_login_returns_token(client):
    response = client.post(
        "/auth/login", json={"email": "alice@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.get_json()


def test_login_failures_are_indistinguishable(client):
    wrong_password = client.post(
        "/auth/login", json={"email": "alice@example.com", "password": "nope-nope"}
    )
    unknown_user = client.post(
        "/auth/login", json={"email": "ghost@example.com", "password": "password123"}
    )
    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.get_json() == unknown_user.get_json()


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_me_returns_current_user(client, login):
    response = client.get("/auth/me", headers=login("alice@example.com"))
    assert response.status_code == 200
    assert response.get_json()["email"] == "alice@example.com"