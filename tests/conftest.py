from datetime import date

import pytest

from app import create_app, db
from app.models import Category, Order, OrderItem, Product, Shipment, User

PASSWORD = "password123"


def _user(name, email):
    user = User(name=name, email=email, role="customer")
    user.set_password(PASSWORD)
    db.session.add(user)
    return user


def _order(user, product, status, shipment=False):
    order = Order(user=user, status=status, total=product.price)
    order.items.append(
        OrderItem(product=product, quantity=1, unit_price=product.price, subtotal=product.price)
    )
    if shipment:
        order.shipment = Shipment(
            carrier="OCA",
            tracking_code="TEST123AR",
            status="delivered",
            estimated_delivery=date(2026, 1, 10),
        )
    db.session.add(order)
    return order


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "JWT_SECRET_KEY": "test-secret-key-for-the-test-suite-0123456789",
        }
    )
    with app.app_context():
        db.create_all()

        genre = Category(name="RPG")
        game = Product(
            name="Chrono Trigger",
            price=59.99,
            product_type="game",
            console="SNES",
            category=genre,
            stock=5,
        )
        db.session.add_all([genre, game])

        alice = _user("Alice", "alice@example.com")
        bob = _user("Bob", "bob@example.com")
        _order(alice, game, "delivered", shipment=True)
        _order(alice, game, "pending")
        _order(bob, game, "delivered", shipment=True)
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def login(client):
    def _login(email):
        response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.get_json()['access_token']}"}

    return _login


@pytest.fixture()
def ids(app):
    def order_id(email, status):
        return (
            Order.query.join(User, User.id == Order.user_id)
            .filter(User.email == email, Order.status == status)
            .one()
            .id
        )

    return {
        "alice_delivered": order_id("alice@example.com", "delivered"),
        "alice_pending": order_id("alice@example.com", "pending"),
        "bob_delivered": order_id("bob@example.com", "delivered"),
        "bob_user": User.query.filter_by(email="bob@example.com").one().id,
    }