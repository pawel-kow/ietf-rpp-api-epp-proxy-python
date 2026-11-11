from connexion import request
from flask import current_app

from core.capabilities.backend_profile import BackendProfile

# The key of the token info that holds the request's backend.
TOKEN_BACKEND = "backend"

# The keys of the application configuration that hold what create_app is given.
BACKEND_PROFILE = "RPP_BACKEND_PROFILE"

DISCOVERY_SETTINGS = "RPP_DISCOVERY_SETTINGS"


def get_backend():
    """
    Get the registry backend of the request's session from the request context.
    """
    if "token_info" not in request.context or TOKEN_BACKEND not in request.context["token_info"]:
        raise ValueError("Registry backend not found in request context")
    return request.context["token_info"][TOKEN_BACKEND]


def backend_profile() -> BackendProfile:
    """What the backend of this application can hold."""
    return current_app.config[BACKEND_PROFILE]


def discovery_settings():
    """What the discovery document states, as configured: rpp_base_url, rpp_tlds, rpp_environment_name and
    rpp_environment_status. None when the application was given none."""
    return current_app.config.get(DISCOVERY_SETTINGS)
