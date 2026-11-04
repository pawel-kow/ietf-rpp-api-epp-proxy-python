from connexion import request, ProblemException
from eppclient.epp_contacts import *
from models import *
from rpp_to_model_mapper import *
from .helper.rpp_response import *
import asyncio
from .auth import get_epp_client

@rpp_operation
def contacts_create(body):
    contact = map_request(rpp_to_contact, body)
    contactresp = epp_contacts_Create(get_epp_client(), contact, client_transaction_id=client_transaction_id())
    if isinstance(contactresp, ErrorResponse):
        raise_epp_error(contactresp)
    inforesp = epp_contacts_Info(get_epp_client(), contactresp.contact.id)
    headers = generate_rpp_response_headers(contactresp)
    headers["Location"] = f"{str(request.url).rstrip('/')}/{contact.id}"
    return contact_to_rpp(inforesp.contact), 201, headers

@rpp_operation
def contacts_delete(id):
    if asyncio.run(request.get_body()):
        raise ProblemException(status=400, title="Bad Request", detail="Request body must be empty for DELETE method")
    contactresp = epp_contacts_Delete(get_epp_client(), id, client_transaction_id=client_transaction_id())
    if isinstance(contactresp, ErrorResponse):
        raise_epp_error(contactresp)
    return None, 200, generate_rpp_response_headers(contactresp)

@rpp_operation
def contacts_read(id):
    contactresp = epp_contacts_Info(get_epp_client(), id, client_transaction_id=client_transaction_id())
    if isinstance(contactresp, ErrorResponse):
        raise_epp_error(contactresp)
    return contact_to_rpp(contactresp.contact), 200, generate_rpp_response_headers(contactresp)
