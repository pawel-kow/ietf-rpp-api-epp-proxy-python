from models import OperationResponse

def clear_empty_value_keys(d: dict) -> dict:
    for key in list(d.keys()):
        if d[key] is None:
            del d[key]
    return d


def generate_rpp_response_headers(resp: OperationResponse) -> dict:
    """Generate the RPP response header."""
    return clear_empty_value_keys({
        "RPP-clTRID": resp.client_transaction_id,
        "RPP-svTRID": resp.server_transaction_id
    })

def generate_rpp_response_headers_separate(
    client_transaction_id: str = None) -> dict:
    """Generate the RPP response header."""
    return clear_empty_value_keys({
        "RPP-clTRID": client_transaction_id
    })

