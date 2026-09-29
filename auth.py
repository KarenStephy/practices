"""
JWT authentication for the visualizer.

Provides:
- init_jwt(app): configures Flask-JWT-Extended's JWTManager on the
  app, plus custom error handlers so any missing/invalid/expired
  token produces the same friendly-but-firm 401 response.
- auth_bp: a Blueprint exposing POST /login, which checks a
  username/password against a small demo user store and, if valid,
  issues a JWT access token.

This is intentionally a minimal auth scheme for a small project: a
hardcoded user dict, not a users table with hashed passwords. Swap
DEMO_USERS for a real lookup (e.g. a User model + password hashing)
before this ever sees real traffic.
"""

import os
from datetime import timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token

# --- demo user store ---
# username -> password. In a real app this would be a database table
# with hashed passwords (e.g. via werkzeug.security or passlib), not
# plaintext in source code.
DEMO_USERS = {
    "admin": "admin123",
    "ivan": "password123",
}

UNAUTHORIZED_BODY = {
    "error": "I don't know you.",
    "message": "Bye.",
}

auth_bp = Blueprint("auth", __name__)


def init_jwt(app):
    """Configure JWTManager on the given Flask app, including custom
    handlers so every "no valid token" case returns the same 401
    response, e.g. requests to /save_analysis with a missing,
    malformed, invalid, or expired token."""
    app.config["JWT_SECRET_KEY"] = os.environ.get(
        "JWT_SECRET_KEY", "dev-secret-change-me-before-deploying"
    )
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)

    jwt = JWTManager(app)

    @jwt.unauthorized_loader
    def missing_token(_reason):
        # No Authorization header at all (or it's not a Bearer header).
        return jsonify(UNAUTHORIZED_BODY), 401

    @jwt.invalid_token_loader
    def invalid_token(_reason):
        # Authorization header present, but the token doesn't verify
        # (bad signature, malformed, wrong type, etc).
        return jsonify(UNAUTHORIZED_BODY), 401

    @jwt.expired_token_loader
    def expired_token(_jwt_header, _jwt_payload):
        return jsonify(UNAUTHORIZED_BODY), 401

    @jwt.revoked_token_loader
    def revoked_token(_jwt_header, _jwt_payload):
        return jsonify(UNAUTHORIZED_BODY), 401

    return jwt


@auth_bp.route("/login", methods=["POST"])
def login():
    """Exchange a username/password for a JWT access token.

    POST /login
    {"username": "admin", "password": "admin123"}

    The token is returned both in the JSON body (`access_token`) and
    in the response's `Authorization` header, as `Bearer <token>`.
    To call a protected endpoint afterwards, send that same value
    back as a request header:

        Authorization: Bearer <token>

    (not as a query parameter).
    """
    data = request.get_json(silent=True) or request.form
    username = data.get("username") if data else None
    password = data.get("password") if data else None

    if not username or not password or DEMO_USERS.get(username) != password:
        return jsonify({"error": "Invalid username or password."}), 401

    access_token = create_access_token(identity=username)

    response = jsonify({
        "message": "Login successful.",
        "access_token": access_token,
        "token_type": "Bearer",
    })
    response.headers["Authorization"] = f"Bearer {access_token}"
    return response, 200
