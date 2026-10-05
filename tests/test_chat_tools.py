import inspect

import pytest

from app import chat, services
from app.models import ReturnRequest, User


@pytest.fixture(autouse=True)
def clean_pending(app):
    # requesting `app` gives every test in this file an app context and a fresh DB
    chat._pending.clear()

def user_id(email):
    return User.query.filter_by(email=email).one().id


def tools_by_name(uid):
    return {tool.__name__: tool for tool in chat.build_tools(uid)}


def test_no_tool_accepts_a_user_id():
    for tool in chat.build_tools(user_id("alice@example.com")):
        assert "user_id" not in inspect.signature(tool).parameters, tool.__name__


def test_tool_signatures_have_no_defaults_or_optionals():
    # the Gemini API schema generator rejects them
    for tool in chat.build_tools(user_id("alice@example.com")):
        for name, param in inspect.signature(tool).parameters.items():
            assert param.default is inspect.Parameter.empty, f"{tool.__name__}.{name}"


def test_tools_only_see_the_callers_data(ids):
    tools = tools_by_name(user_id("alice@example.com"))
    mine = tools["get_my_orders"]("", 10)
    assert {o["id"] for o in mine["items"]} == {ids["alice_delivered"], ids["alice_pending"]}
    assert tools["get_order_details"](ids["bob_delivered"]) == {"error": "Order not found"}
    assert tools["track_shipment"](ids["bob_delivered"]) == {"error": "Order not found"}


def test_bad_arguments_come_back_as_an_error_dict():
    tools = tools_by_name(user_id("alice@example.com"))
    assert tools["get_order_details"]("not-a-number") == {"error": "Invalid arguments"}
    assert "error" in tools["purchase_stats"]("password_hash", 0)


def test_request_return_does_not_write_until_confirmed(ids):
    uid = user_id("alice@example.com")
    result = tools_by_name(uid)["request_return"](ids["alice_delivered"], "Disc arrived scratched")
    assert result["status"] == "awaiting_customer_confirmation"
    assert ReturnRequest.query.count() == 0
    assert chat.get_pending(uid)["order_id"] == ids["alice_delivered"]

    chat.confirm_pending_return(uid)
    assert ReturnRequest.query.count() == 1


def test_request_return_on_someone_elses_order_creates_no_pending(ids):
    uid = user_id("alice@example.com")
    result = tools_by_name(uid)["request_return"](ids["bob_delivered"], "Disc arrived scratched")
    assert result == {"error": "Order not found"}
    assert chat.get_pending(uid) is None


def test_spending_summary_and_top_products_only_count_own_orders():
    alice = services.spending_summary(user_id("alice@example.com"))
    bob = services.spending_summary(user_id("bob@example.com"))
    assert (alice["orders"], bob["orders"]) == (2, 1)
    assert alice["total_spent"] == 119.98

    top = services.top_products(user_id("alice@example.com"))
    assert top[0]["product"] == "Chrono Trigger" and top[0]["units"] == 2


def test_ask_requires_token(client):
    assert client.post("/ask", json={"message": "hola"}).status_code == 401


def test_ask_rejects_empty_message_before_calling_the_llm(client, login):
    response = client.post("/ask", json={"message": "  "}, headers=login("alice@example.com"))
    assert response.status_code == 400


def test_confirm_without_pending_action_is_404(client, login):
    response = client.post("/ask/confirm", headers=login("alice@example.com"))
    assert response.status_code == 404