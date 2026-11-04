from connexion import request


def get_epp_client():
    """
    Get the EPP client from the request context.
    """
    if "token_info" not in request.context or "epp_client" not in request.context["token_info"]:
        raise ValueError("EPP client not found in request context")
    return request.context["token_info"]["epp_client"]
