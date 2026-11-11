from connexion import request
from flask import current_app

from core.capabilities.backend_profile import BackendProfile

# The key of the token info that holds the request's backend.
TOKEN_BACKEND = "backend"


def get_backend():
    """
    Get the registry backend of the request's session from the request context.
    """
    if "token_info" not in request.context or TOKEN_BACKEND not in request.context["token_info"]:
        raise ValueError("Registry backend not found in request context")
    return request.context["token_info"][TOKEN_BACKEND]


def backend_profile() -> BackendProfile:
    """What the backend of this application can hold."""
    return current_app.config["RPP_BACKEND_PROFILE"]
