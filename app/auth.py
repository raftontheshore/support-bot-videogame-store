import re

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from app import db
from app.models import User
from app.services import ConflictError, ValidationError

bp = Blueprint("auth", __name__, url_prefix="/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")

    if not name or len(name) > 100:
        raise ValidationError("name is required (max 100 characters)")
    if not EMAIL_RE.match(email) or len(email) > 120:
        raise ValidationError("a valid email is required")
    if len(password) < 8:
        raise ValidationError("password must have at least 8 characters")
    if User.query.filter_by(email=email).first():
        raise ConflictError("Email already registered")

    # role is never read from the request: everyone who registers is a customer
    user = User(name=name, email=email, role="customer")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify(id=user.id, name=user.name, email=user.email), 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")

    user = User.query.filter_by(email=email).first()
    # same response for unknown email, wrong password or inactive account
    if user is None or not user.active or not user.check_password(password):
        return jsonify(error="Invalid credentials"), 401

    # identity must be a string; the role goes in the token as an extra claim
    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return jsonify(access_token=token, token_type="Bearer")


@bp.get("/me")
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None or not user.active:
        return jsonify(error="Invalid token"), 401
    return jsonify(id=user.id, name=user.name, email=user.email, role=user.role)