from models import OperationResponse, ResultCode

def clear_empty_value_keys(d: dict) -> dict:
    for key in list(d.keys()):
        if d[key] is None:
            del d[key]
    return d


def generate_rpp_response_headers(resp: OperationResponse) -> dict:
    """Generate the RPP response header."""
    return clear_empty_value_keys({
        "Content-Type": "application/json",
        "RPP-clTRID": resp.client_transaction_id,
        "RPP-svTRID": resp.server_transaction_id,
        "RPP-code": resp.code.value[0] if resp.code else None,
        "RPP-code-text": resp.code.value[1] if resp.code else None,
    })

def generate_rpp_response_headers_separate(
    client_transaction_id: str = None, code: ResultCode = None) -> dict:
    """Generate the RPP response header."""
    return clear_empty_value_keys({
        "Content-Type": "application/json",
        "RPP-clTRID": client_transaction_id,
        "RPP-code": code.value[0] if code else None,
        "RPP-code-text": code.value[1] if code else None,
    })

