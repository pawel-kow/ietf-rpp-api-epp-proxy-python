from connexion import request

from core.flows.contact.contact_flows import create_contact, patch_contact, replace_contact
from core.result.error_response import ErrorResponse
from rpp.handlers.shared.requested_elements import requested_elements
from rpp.http.context import backend_profile, get_backend
from rpp.http.headers import client_transaction_id, generate_rpp_response_headers
from rpp.http.operation import map_request, require_empty_body, rpp_operation
from rpp.http.problem import raise_registry_error
from rpp.mapping.contact import contact_availability, contact_patch, contact_replacement, contacts
from rpp.mapping.contact.contact_capabilities import check_contact, check_contact_update
from rpp.mapping.shared import include_elements

OBJECT = "contact"


def _contact_output(contact, requested):
    """The contact as a response shows it: with the onDemand data elements the request includes."""
    return include_elements.visible(OBJECT, contacts.model_to_rpp(contact), requested)


@rpp_operation
def contacts_create(body):
    requested = requested_elements(OBJECT)
    contact = map_request(check_contact, map_request(contacts.rpp_to_model, body), profile=backend_profile())
    result = create_contact(get_backend(), contact, client_transaction_id())
    return _mutation_answer(result, requested, 201, {"Location": f"{str(request.url).rstrip('/')}/{contact.id}"})

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
    return _contact_output(contactresp.payload, requested), 200, generate_rpp_response_headers(contactresp)


def _mutation_answer(result, requested, status=200, extra_headers=None):
    """The answer to a mutation: the contact as read after it, or 202 with no body when that read failed."""
    if isinstance(result, ErrorResponse):
        raise_registry_error(result)
    headers = {**generate_rpp_response_headers(result.mutation), **(extra_headers or {})}
    if result.stored is None:
        return None, 202, headers
    return _contact_output(result.stored, requested), status, headers


@rpp_operation
def contacts_update(id, body):
    requested = requested_elements(OBJECT)
    wanted = map_request(check_contact, map_request(contact_replacement.rpp_to_model, id, body, requested),
                         profile=backend_profile())
    return _mutation_answer(replace_contact(get_backend(), wanted, client_transaction_id()), requested)


@rpp_operation
def contacts_updatePartial(id, body):
    requested = requested_elements(OBJECT)
    update = map_request(check_contact_update, map_request(contact_patch.rpp_to_model, id, body), profile=backend_profile())

    def wanted_from_current(current):
        return map_request(check_contact, map_request(contact_patch.rpp_to_model_with_current, id, body, current,
                                       kind_held=backend_profile().contact_kind_held),
                           profile=backend_profile())

    return _mutation_answer(patch_contact(get_backend(), id, update, wanted_from_current, client_transaction_id()), requested)


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
    return None, 200 if ret.payload.available else 404, headers

@rpp_operation
def contacts_availability(id):
    ret = _availability(id)
    return contact_availability.model_to_rpp(ret.payload), 200 if ret.payload.available else 404, generate_rpp_response_headers(ret)
