import os
from eppclient.eppclient import EPPClient
from connexion import request
from config import config

os.environ["BASICINFO_FUNC"] = 'controller.basic_auth'

CLIENTS = {
}

def basic_auth(username, password):
    client = CLIENTS.get(username)
    if client is None:
        new_client = EPPClient(config.rpp_epp_host, config.rpp_epp_port, username, password)
        new_client.connect()
        if not new_client.connected:
            return None
        # Concurrent first requests may each log in. setdefault is atomic, so exactly
        # one session is kept for the user and all requests share it.
        client = CLIENTS.setdefault(username, new_client)
        if client is not new_client:
            new_client.disconnect()

    if not client.verify_credentials(username, password):
        return None

    return {
        "epp_client": client
    }

def get_epp_client():
    """
    Get the EPP client from the request context.
    """
    if "token_info" not in request.context or "epp_client" not in request.context["token_info"]:
        raise ValueError("EPP client not found in request context")
    return request.context["token_info"]["epp_client"]
