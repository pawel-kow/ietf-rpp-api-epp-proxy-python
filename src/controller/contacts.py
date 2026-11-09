from connexion import request
from eppclient.epp_contacts import *
from models import *
import rpp_to_model_mapper as rpp_mapper
from .helper.rpp_response import *
from .auth import get_epp_client

@rpp_operation
def contacts_create(body):
    contact = map_request(rpp_mapper.contacts.rpp_to_model, body)
    contactresp = epp_contacts_Create(get_epp_client(), contact, client_transaction_id=client_transaction_id())
    if isinstance(contactresp, ErrorResponse):
        raise_epp_error(contactresp)
    inforesp = epp_contacts_Info(get_epp_client(), contactresp.contact.id)
    headers = generate_rpp_response_headers(contactresp)
    headers["Location"] = f"{str(request.url).rstrip('/')}/{contact.id}"
    return rpp_mapper.contacts.model_to_rpp(inforesp.contact), 201, headers

@rpp_operation
def contacts_delete(id):
    require_empty_body()
    contactresp = epp_contacts_Delete(get_epp_client(), id, client_transaction_id=client_transaction_id())
    if isinstance(contactresp, ErrorResponse):
        raise_epp_error(contactresp)
    return None, 200, generate_rpp_response_headers(contactresp)

@rpp_operation
def contacts_read(id):
    contactresp = epp_contacts_Info(get_epp_client(), id, client_transaction_id=client_transaction_id())
    if isinstance(contactresp, ErrorResponse):
        raise_epp_error(contactresp)
    return rpp_mapper.contacts.model_to_rpp(contactresp.contact), 200, generate_rpp_response_headers(contactresp)


def _availability(id):
    ret = epp_contacts_Check(get_epp_client(), id, client_transaction_id=client_transaction_id())
    if isinstance(ret, ErrorResponse):
        raise_epp_error(ret)
    return ret

@rpp_operation
def contacts_availabilityHead(id):
    ret = _availability(id)
    headers = generate_rpp_response_headers(ret)
    del headers["Content-Type"]  # the OpenAPI defines no content for HEAD
    return None, 200 if ret.available else 404, headers

@rpp_operation
def contacts_availability(id):
    ret = _availability(id)
    return rpp_mapper.contact_availability.model_to_rpp(ret), 200 if ret.available else 404, generate_rpp_response_headers(ret)
