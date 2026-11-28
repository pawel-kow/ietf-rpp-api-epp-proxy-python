from registry_adapter.rri.commands.contact.info import is_request, not_found, rri_info
from registry_adapter.rri.extensions.rri.commands.request_contact.common import request_contact_from_rri


def rri_request_contact_info(client, handle: str, client_transaction_id=None):
    """Contact INFO of a REQUEST contact. A PERSON or an ORG is a contact, not a request contact."""
    resp = rri_info(client, handle, client_transaction_id)
    data = getattr(resp, "payload", None)
    if data is None:
        return resp
    if not is_request(data):
        return not_found(handle, "a request contact", client_transaction_id)
    resp.payload = request_contact_from_rri(data)
    return resp
