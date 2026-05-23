from __future__ import annotations

import os
import secrets
from functools import wraps
from typing import Any, Callable

from flask import jsonify, session


DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASS = "copper2026"


def get_admin_credentials() -> tuple[str, str]:
    """Return admin username and password from env or defaults."""
    username = os.getenv("ADMIN_USERNAME", DEFAULT_ADMIN_USER)
    password = os.getenv("ADMIN_PASSWORD", DEFAULT_ADMIN_PASS)
    return username, password


def verify_admin(username: str, password: str) -> bool:
    """Validate admin credentials using constant-time comparison."""
    expected_user, expected_pass = get_admin_credentials()
    user_ok = secrets.compare_digest(username.encode(), expected_user.encode())
    pass_ok = secrets.compare_digest(password.encode(), expected_pass.encode())
    return user_ok and pass_ok


def admin_required(f: Callable[..., Any]) -> Callable[..., Any]:
    """Flask route decorator that requires admin authentication via session."""
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        if not session.get("is_admin"):
            return jsonify({"error": "Authentication required."}), 401
        return f(*args, **kwargs)
    return decorated
