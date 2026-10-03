from sqlalchemy import extract, func

from app import db
from app.models import Category, Order, OrderItem, Product


def purchases_by_month(user_id):
    """Games bought per month by this user, best month first."""
    year = extract("year", Order.order_date)
    month = extract("month", Order.order_date)
    games = func.sum(OrderItem.quantity)

    rows = (
        db.session.query(year.label("year"), month.label("month"), games.label("games"))
        .select_from(Order)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .join(Product, Product.id == OrderItem.product_id)
        .filter(
            Order.user_id == user_id,
            Order.status != "cancelled",
            Product.product_type == "game",
        )
        .group_by(year, month)
        .order_by(games.desc(), year.desc(), month.desc())
        .all()
    )
    return [{"year": int(r.year), "month": int(r.month), "games": int(r.games)} for r in rows]


def top_genres(user_id, limit=5):
    """Most purchased genres by this user."""
    games = func.sum(OrderItem.quantity)

    rows = (
        db.session.query(Category.name, games.label("games"))
        .select_from(Order)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .join(Product, Product.id == OrderItem.product_id)
        .join(Category, Category.id == Product.category_id)
        .filter(Order.user_id == user_id, Order.status != "cancelled")
        .group_by(Category.name)
        .order_by(games.desc())
        .limit(limit)
        .all()
    )
    return [{"genre": r[0], "games": int(r[1])} for r in rows]