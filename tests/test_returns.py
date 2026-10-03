def post_return(client, headers, order_id, reason="Disc arrived scratched"):
    return client.post("/returns", json={"order_id": order_id, "reason": reason}, headers=headers)


def test_return_for_delivered_order_is_created(client, login, ids):
    response = post_return(client, login("alice@example.com"), ids["alice_delivered"])
    assert response.status_code == 201
    assert response.get_json()["status"] == "pending"


def test_cannot_return_an_order_that_is_not_delivered(client, login, ids):
    response = post_return(client, login("alice@example.com"), ids["alice_pending"])
    assert response.status_code == 409


def test_duplicate_pending_return_is_409(client, login, ids):
    headers = login("alice@example.com")
    assert post_return(client, headers, ids["alice_delivered"]).status_code == 201
    assert post_return(client, headers, ids["alice_delivered"]).status_code == 409


def test_return_reason_is_validated(client, login, ids):
    response = post_return(client, login("alice@example.com"), ids["alice_delivered"], reason="no")
    assert response.status_code == 400