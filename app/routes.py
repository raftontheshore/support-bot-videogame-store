from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import services
from app.services import ValidationError

bp = Blueprint("api", __name__)


def current_user_id():
    """The ONLY source of user_id: the verified JWT. Never the request body or query string."""
    return int(get_jwt_identity())


def page_args():
    return request.args.get("page", 1, type=int), request.args.get("per_page", 20, type=int)


@bp.get("/health")
def health():
    return jsonify(status="ok")


# ---------- public ----------


@bp.get("/products")
def products():
    page, per_page = page_args()
    return jsonify(
        services.search_products(
            q=request.args.get("q"),
            genre=request.args.get("genre"),
            console=request.args.get("console"),
            page=page,
            per_page=per_page,
        )
    )


# ---------- protected ----------


@bp.get("/orders")
@jwt_required()
def orders():
    page, per_page = page_args()
    return jsonify(
        services.list_orders(
            current_user_id(), status=request.args.get("status"), page=page, per_page=per_page
        )
    )


@bp.get("/orders/<int:order_id>")
@jwt_required()
def order_detail(order_id):
    return jsonify(services.get_order(current_user_id(), order_id))


@bp.get("/orders/<int:order_id>/shipment")
@jwt_required()
def order_shipment(order_id):
    return jsonify(services.get_shipment(current_user_id(), order_id))


@bp.get("/returns")
@jwt_required()
def returns_list():
    return jsonify(services.list_returns(current_user_id()))


@bp.post("/returns")
@jwt_required()
def returns_create():
    data = request.get_json(silent=True) or {}
    order_id = data.get("order_id")
    if not isinstance(order_id, int) or isinstance(order_id, bool):
        raise ValidationError("order_id must be an integer")
    created = services.create_return(current_user_id(), order_id, data.get("reason"))
    return jsonify(created), 201


@bp.get("/stats/purchases")
@jwt_required()
def stats_purchases():
    group_by = request.args.get("group_by", "month")
    year = request.args.get("year", type=int)
    results = services.purchase_stats(current_user_id(), group_by, year)
    return jsonify(group_by=group_by, year=year, results=results)