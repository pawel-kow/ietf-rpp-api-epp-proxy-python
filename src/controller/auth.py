import os
from eppclient.eppclient import EPPClient
from connexion import request

os.environ["BASICINFO_FUNC"] = 'controller.basic_auth'

CLIENTS = {
}

def basic_auth(username, password):
    if CLIENTS.get(username) is None:
        client = EPPClient("localhost", 7001, username, password)
        client.connect()
        if not client.connected:
            return None
        CLIENTS[username] = client
    else:
        if not CLIENTS[username].verify_credentials(username, password):
            return None

    return {
        "epp_client": CLIENTS[username]
    }

def get_epp_client():
    """
    Get the EPP client from the request context.
    """
    if "token_info" not in request.context or "epp_client" not in request.context["token_info"]:
        raise ValueError("EPP client not found in request context")
    return request.context["token_info"]["epp_client"]
