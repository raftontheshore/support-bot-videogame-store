import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

db = SQLAlchemy()
jwt = JWTManager()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///app.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)

    if test_config:
        app.config.update(test_config)
    if not app.config["JWT_SECRET_KEY"]:
        raise RuntimeError("JWT_SECRET_KEY is not set. Copy .env.example to .env and set it.")

    app.json.sort_keys = False  # keep field order in JSON responses

    db.init_app(app)
    jwt.init_app(app)

    from app import models  # noqa: F401  (registers the models)
    from app.auth import bp as auth_bp
    from app.routes import bp as api_bp
    from app.services import ServiceError

    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)

    @app.errorhandler(ServiceError)
    def handle_service_error(err):
        return jsonify(error=err.message), err.status_code

    @app.errorhandler(404)
    def handle_404(_err):
        return jsonify(error="Not found"), 404

    @app.errorhandler(405)
    def handle_405(_err):
        return jsonify(error="Method not allowed"), 405

    @jwt.unauthorized_loader
    def missing_token(_reason):
        return jsonify(error="Authentication required"), 401

    @jwt.invalid_token_loader
    def invalid_token(_reason):
        return jsonify(error="Invalid token"), 401

    @jwt.expired_token_loader
    def expired_token(_header, _payload):
        return jsonify(error="Token expired"), 401

    return app