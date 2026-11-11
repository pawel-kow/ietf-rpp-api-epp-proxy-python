from connexion import request


def get_backend():
    """
    Get the registry backend of the request's session from the request context.
    """
    if "token_info" not in request.context or "backend" not in request.context["token_info"]:
        raise ValueError("Registry backend not found in request context")
    return request.context["token_info"]["backend"]
