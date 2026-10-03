from app.models import ReturnRequest


def order_ids(response):
    return {o["id"] for o in response.get_json()["items"]}


def test_orders_require_token(client):
    assert client.get("/orders").status_code == 401


def test_list_orders_only_returns_own(client, login, ids):
    response = client.get("/orders", headers=login("alice@example.com"))
    assert order_ids(response) == {ids["alice_delivered"], ids["alice_pending"]}


def test_user_id_query_param_is_ignored(client, login, ids):
    response = client.get(
        f"/orders?user_id={ids['bob_user']}", headers=login("alice@example.com")
    )
    assert ids["bob_delivered"] not in order_ids(response)


def test_other_users_order_is_404_and_looks_like_a_missing_one(client, login, ids):
    headers = login("alice@example.com")
    other = client.get(f"/orders/{ids['bob_delivered']}", headers=headers)
    missing = client.get("/orders/999999", headers=headers)
    assert other.status_code == missing.status_code == 404
    assert other.get_json() == missing.get_json()


def test_other_users_shipment_is_404_and_looks_like_a_missing_one(client, login, ids):
    headers = login("alice@example.com")
    other = client.get(f"/orders/{ids['bob_delivered']}/shipment", headers=headers)
    missing = client.get("/orders/999999/shipment", headers=headers)
    assert other.status_code == missing.status_code == 404
    assert other.get_json() == missing.get_json()


def test_own_shipment_is_visible(client, login, ids):
    response = client.get(
        f"/orders/{ids['alice_delivered']}/shipment", headers=login("alice@example.com")
    )
    assert response.status_code == 200
    assert response.get_json()["tracking_code"] == "TEST123AR"


def test_cannot_return_other_users_order(client, login, ids):
    response = client.post(
        "/returns",
        json={"order_id": ids["bob_delivered"], "reason": "Disc arrived scratched"},
        headers=login("alice@example.com"),
    )
    assert response.status_code == 404
    assert ReturnRequest.query.count() == 0


def test_stats_only_count_own_purchases(client, login):
    alice = client.get("/stats/purchases?group_by=genre", headers=login("alice@example.com"))
    bob = client.get("/stats/purchases?group_by=genre", headers=login("bob@example.com"))
    assert sum(r["games"] for r in alice.get_json()["results"]) == 2
    assert sum(r["games"] for r in bob.get_json()["results"]) == 1


def test_stats_group_by_is_whitelisted(client, login):
    response = client.get(
        "/stats/purchases?group_by=password_hash", headers=login("alice@example.com")
    )
    assert response.status_code == 400