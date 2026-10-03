from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from app import db


def utcnow():
    return datetime.now(timezone.utc)


def money():
    # asdecimal=False: returns floats (SQLite has no native Decimal and JSON-friendly).
    # In production: Numeric with asdecimal=True or integer cents.
    return db.Numeric(10, 2, asdecimal=False)


class Category(db.Model):
    """Game genre (RPG, Racing, Fighting, etc.)."""

    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255))

    products = db.relationship("Product", back_populates="category")


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(500))
    original_price = db.Column(money())
    price = db.Column(money(), nullable=False)
    discount_percentage = db.Column(db.Numeric(5, 2, asdecimal=False), default=0)
    stock = db.Column(db.Integer, default=0)
    low_stock = db.Column(db.Boolean, default=False)
    brand = db.Column(db.String(50))
    console = db.Column(db.String(30))
    product_type = db.Column(db.String(20), index=True)  # game | console | accessory
    active = db.Column(db.Boolean, default=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)

    category = db.relationship("Category", back_populates="products")


class Address(db.Model):
    __tablename__ = "addresses"

    id = db.Column(db.Integer, primary_key=True)
    postal_code = db.Column(db.String(10))
    street = db.Column(db.String(150))
    province = db.Column(db.String(60))
    city = db.Column(db.String(80))


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="customer")  # customer | admin
    active = db.Column(db.Boolean, default=True)
    phone = db.Column(db.String(30))
    address_id = db.Column(db.Integer, db.ForeignKey("addresses.id"), unique=True, nullable=True)

    address = db.relationship("Address")
    orders = db.relationship("Order", back_populates="user")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Order(db.Model):
    """venta_cabecera"""

    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_date = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    total = db.Column(money(), nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    address_id = db.Column(db.Integer, db.ForeignKey("addresses.id"), nullable=True)

    user = db.relationship("User", back_populates="orders")
    address = db.relationship("Address")
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    shipment = db.relationship(
        "Shipment", back_populates="order", uselist=False, cascade="all, delete-orphan"
    )
    returns = db.relationship("ReturnRequest", back_populates="order", cascade="all, delete-orphan")


class OrderItem(db.Model):
    """venta_detalle"""

    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(money(), nullable=False)  # price paid at purchase time
    subtotal = db.Column(money(), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product")


class Shipment(db.Model):
    __tablename__ = "shipments"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), unique=True, nullable=False)
    carrier = db.Column(db.String(50), nullable=False)
    tracking_code = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(30), nullable=False)  # in_transit | delivered
    estimated_delivery = db.Column(db.Date)

    order = db.relationship("Order", back_populates="shipment")


class ReturnRequest(db.Model):
    __tablename__ = "return_requests"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    reason = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    order = db.relationship("Order", back_populates="returns")