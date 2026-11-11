from connexion import request
from core.result.error_response import ErrorResponse
import rpp_to_model_mapper as rpp_mapper
from .helper.rpp_response import *
from core.flows.contact.contact_flows import patch_contact, replace_contact
from .auth import get_backend

OBJECT = "contact"


def _contact_output(contact, requested):
    """The contact as a response shows it: with the onDemand data elements the request includes."""
    return rpp_mapper.include_elements.visible(OBJECT, rpp_mapper.contacts.model_to_rpp(contact), requested)


@rpp_operation
def contacts_create(body):
    requested = requested_elements(OBJECT)
    contact = map_request(rpp_mapper.contacts.rpp_to_model, body)
    contactresp = get_backend().contacts.create(contact, client_transaction_id=client_transaction_id())
    if isinstance(contactresp, ErrorResponse):
        raise_registry_error(contactresp)
    inforesp = get_backend().contacts.info(contactresp.contact.id)
    headers = generate_rpp_response_headers(contactresp)
    headers["Location"] = f"{str(request.url).rstrip('/')}/{contact.id}"
    return _contact_output(inforesp.contact, requested), 201, headers

@rpp_operation
def contacts_delete(id):
    require_empty_body()
    contactresp = get_backend().contacts.delete(id, client_transaction_id=client_transaction_id())
    if isinstance(contactresp, ErrorResponse):
        raise_registry_error(contactresp)
    return None, 200, generate_rpp_response_headers(contactresp)

@rpp_operation
def contacts_read(id):
    requested = requested_elements(OBJECT)
    contactresp = get_backend().contacts.info(id, client_transaction_id=client_transaction_id())
    if isinstance(contactresp, ErrorResponse):
        raise_registry_error(contactresp)
    return _contact_output(contactresp.contact, requested), 200, generate_rpp_response_headers(contactresp)


def _updated_contact(result, requested):
    """The answer to an update: the contact as read after it, or 202 when that read failed."""
    if isinstance(result, ErrorResponse):
        raise_registry_error(result)
    headers = generate_rpp_response_headers(result.mutation)
    if result.contact is None:
        return None, 202, headers
    return _contact_output(result.contact, requested), 200, headers


@rpp_operation
def contacts_update(id, body):
    requested = requested_elements(OBJECT)
    wanted = map_request(rpp_mapper.contact_replacement.rpp_to_model, id, body, requested)
    return _updated_contact(replace_contact(get_backend(), wanted, client_transaction_id()), requested)


@rpp_operation
def contacts_updatePartial(id, body):
    requested = requested_elements(OBJECT)
    update = map_request(rpp_mapper.contact_patch.rpp_to_model, id, body)

    def wanted_from_current(current):
        return map_request(rpp_mapper.contact_patch.rpp_to_model_with_current, id, body, current)

    return _updated_contact(patch_contact(get_backend(), id, update, wanted_from_current, client_transaction_id()), requested)


def _availability(id):
    ret = get_backend().contacts.check(id, client_transaction_id=client_transaction_id())
    if isinstance(ret, ErrorResponse):
        raise_registry_error(ret)
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
