from sqlalchemy import extract, func
from sqlalchemy.orm import selectinload

from app import db
from app.models import Category, Order, OrderItem, Product, ReturnRequest

ORDER_STATUSES = {"pending", "shipped", "delivered", "cancelled"}
STATS_GROUPINGS = {"month", "genre", "console"}


# ---------- errors (mapped to HTTP codes in create_app) ----------


class ServiceError(Exception):
    status_code = 400

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class ValidationError(ServiceError):
    status_code = 400


class NotFoundError(ServiceError):
    status_code = 404


class ConflictError(ServiceError):
    status_code = 409


# ---------- serializers (whitelist of fields: nothing sensitive leaks) ----------


def _product_dict(p):
    return {
        "id": p.id,
        "name": p.name,
        "type": p.product_type,
        "genre": p.category.name if p.category else None,
        "console": p.console,
        "brand": p.brand,
        "price": p.price,
        "original_price": p.original_price,
        "discount_percentage": p.discount_percentage,
        "in_stock": (p.stock or 0) > 0,
    }


def _return_dict(r):
    return {
        "id": r.id,
        "order_id": r.order_id,
        "reason": r.reason,
        "status": r.status,
        "created_at": r.created_at.isoformat(),
    }


def _shipment_dict(s):
    return {
        "order_id": s.order_id,
        "carrier": s.carrier,
        "tracking_code": s.tracking_code,
        "status": s.status,
        "estimated_delivery": s.estimated_delivery.isoformat() if s.estimated_delivery else None,
    }


def _order_dict(order, detail=False):
    data = {
        "id": order.id,
        "date": order.order_date.isoformat(),
        "status": order.status,
        "total": order.total,
        "item_count": sum(i.quantity for i in order.items),
    }
    if detail:
        data["items"] = [
            {
                "product_id": i.product_id,
                "product": i.product.name,
                "console": i.product.console,
                "quantity": i.quantity,
                "unit_price": i.unit_price,
                "subtotal": i.subtotal,
            }
            for i in order.items
        ]
        addr = order.address
        data["shipping_address"] = f"{addr.street}, {addr.city}, {addr.province}" if addr else None
        data["has_shipment"] = order.shipment is not None
        data["returns"] = [_return_dict(r) for r in order.returns]
    return data


def _paginate(query, page, per_page, serialize):
    page = max(page or 1, 1)
    per_page = min(max(per_page or 20, 1), 100)
    result = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        "items": [serialize(x) for x in result.items],
        "page": result.page,
        "per_page": result.per_page,
        "total": result.total,
        "pages": result.pages,
    }


# ---------- public catalog ----------


def search_products(q=None, genre=None, console=None, page=1, per_page=20):
    query = Product.query.outerjoin(Product.category).filter(Product.active.is_(True))
    if q and q.strip():
        query = query.filter(Product.name.ilike(f"%{q.strip()}%"))
    if genre:
        query = query.filter(func.lower(Category.name) == genre.strip().lower())
    if console:
        query = query.filter(func.lower(Product.console) == console.strip().lower())
    return _paginate(query.order_by(Product.name), page, per_page, _product_dict)


# ---------- per-user data: user_id is ALWAYS required and always filters ----------


def _own_order(user_id, order_id):
    order = Order.query.filter_by(id=order_id, user_id=user_id).first()
    if order is None:
        # same error for "doesn't exist" and "belongs to someone else"
        raise NotFoundError("Order not found")
    return order


def list_orders(user_id, status=None, page=1, per_page=20):
    query = Order.query.filter(Order.user_id == user_id).options(selectinload(Order.items))
    if status:
        if status not in ORDER_STATUSES:
            raise ValidationError(f"status must be one of: {', '.join(sorted(ORDER_STATUSES))}")
        query = query.filter(Order.status == status)
    return _paginate(query.order_by(Order.order_date.desc()), page, per_page, _order_dict)


def get_order(user_id, order_id):
    return _order_dict(_own_order(user_id, order_id), detail=True)


def get_shipment(user_id, order_id):
    order = _own_order(user_id, order_id)
    if order.shipment is None:
        raise NotFoundError("This order has no shipment yet")
    return _shipment_dict(order.shipment)


def list_returns(user_id):
    rows = (
        ReturnRequest.query.join(Order, Order.id == ReturnRequest.order_id)
        .filter(Order.user_id == user_id)
        .order_by(ReturnRequest.created_at.desc())
        .all()
    )
    return [_return_dict(r) for r in rows]


def create_return(user_id, order_id, reason):
    if not isinstance(reason, str) or not 5 <= len(reason.strip()) <= 255:
        raise ValidationError("reason must be a text between 5 and 255 characters")

    order = _own_order(user_id, order_id)
    if order.status != "delivered":
        raise ConflictError("Only delivered orders can be returned")
    if any(r.status == "pending" for r in order.returns):
        raise ConflictError("This order already has a pending return")

    ret = ReturnRequest(order=order, reason=reason.strip(), status="pending")
    db.session.add(ret)
    db.session.commit()
    return _return_dict(ret)


def purchase_stats(user_id, group_by, year=None):
    """Games bought by this user, grouped by month | genre | console.

    group_by is validated against a whitelist: user input never reaches the SQL.
    """
    if group_by not in STATS_GROUPINGS:
        raise ValidationError(f"group_by must be one of: {', '.join(sorted(STATS_GROUPINGS))}")

    games = func.sum(OrderItem.quantity)
    spent = func.sum(OrderItem.subtotal)

    if group_by == "month":
        year_col = extract("year", Order.order_date)
        month_col = extract("month", Order.order_date)
        keys = [year_col.label("year"), month_col.label("month")]
        group_cols = [year_col, month_col]
    elif group_by == "genre":
        keys = [Category.name.label("genre")]
        group_cols = [Category.name]
    else:
        keys = [Product.console.label("console")]
        group_cols = [Product.console]

    query = (
        db.session.query(*keys, games.label("games"), spent.label("spent"))
        .select_from(Order)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .join(Product, Product.id == OrderItem.product_id)
    )
    if group_by == "genre":
        query = query.join(Category, Category.id == Product.category_id)

    query = query.filter(
        Order.user_id == user_id,
        Order.status != "cancelled",
        Product.product_type == "game",
    )
    if year is not None:
        query = query.filter(extract("year", Order.order_date) == year)

    rows = query.group_by(*group_cols).order_by(games.desc(), *group_cols).all()

    results = []
    for row in rows:
        item = row._asdict()
        for key in ("year", "month", "games"):
            if key in item:
                item[key] = int(item[key])
        item["spent"] = round(float(item["spent"]), 2)
        results.append(item)
    return results


# kept for scripts/check_stats.py
def purchases_by_month(user_id):
    return purchase_stats(user_id, "month")


def top_genres(user_id, limit=5):
    return purchase_stats(user_id, "genre")[:limit]