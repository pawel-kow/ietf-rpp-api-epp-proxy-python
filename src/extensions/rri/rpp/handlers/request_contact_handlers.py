"""The request contacts of the rri extension (docs/rri/rri-extension.md), at the paths `create_app` adds where the
backend profile offers it."""
from connexion import request
from flask import request as flask_request

from core.result.error_response import ErrorResponse
from extensions.rri.core.flows.request_contact_flows import (
    create_request_contact, patch_request_contact, replace_request_contact,
)
from extensions.rri.rpp.handlers.rri_gateways import gateways
from extensions.rri.rpp.mapping import (
    request_contact_availability, request_contact_patch, request_contact_replacement, request_contacts,
)
from rpp.handlers.shared.requested_elements import INCLUDE_ELEMENTS
from rpp.http.context import get_backend, request_profile
from rpp.http.headers import client_transaction_id, generate_rpp_response_headers
from rpp.http.operation import map_request, require_empty_body, rpp_operation
from rpp.http.problem import raise_registry_error


def _no_elements_requested():
    map_request(request_contacts.check_requested, flask_request.args.getlist(INCLUDE_ELEMENTS))


def _mutation_answer(result, status=200, extra_headers=None):
    """The answer to a mutation: the request contact as read after it, or 202 with no body when that read failed."""
    if isinstance(result, ErrorResponse):
        raise_registry_error(result)
    headers = {**generate_rpp_response_headers(result.mutation), **(extra_headers or {})}
    if result.stored is None:
        return None, 202, headers
    return request_contacts.model_to_rpp(result.stored, request_profile().extensions), status, headers


@rpp_operation
def requestContacts_create(body):
    _no_elements_requested()
    contact = map_request(request_contacts.rpp_to_model, body, request_profile().extensions)
    result = create_request_contact(get_backend(), contact, client_transaction_id())
    return _mutation_answer(result, 201, {"Location": f"{str(request.url).rstrip('/')}/{contact.id}"})


@rpp_operation
def requestContacts_read(id):
    _no_elements_requested()
    response = gateways().request_contacts.info(id, client_transaction_id=client_transaction_id())
    if isinstance(response, ErrorResponse):
        raise_registry_error(response)
    return (request_contacts.model_to_rpp(response.payload, request_profile().extensions), 200,
            generate_rpp_response_headers(response))


@rpp_operation
def requestContacts_update(id, body):
    _no_elements_requested()
    wanted = map_request(request_contact_replacement.rpp_to_model, id, body, request_profile().extensions)
    return _mutation_answer(replace_request_contact(get_backend(), wanted, client_transaction_id()))


@rpp_operation
def requestContacts_updatePartial(id, body):
    _no_elements_requested()

    def wanted_from_current(current):
        return map_request(request_contact_patch.rpp_to_model_with_current, id, body, current,
                           request_profile().extensions)

    return _mutation_answer(patch_request_contact(get_backend(), id, wanted_from_current, client_transaction_id()))


@rpp_operation
def requestContacts_delete(id):
    require_empty_body()
    response = gateways().request_contacts.delete(id, client_transaction_id=client_transaction_id())
    if isinstance(response, ErrorResponse):
        raise_registry_error(response)
    return None, 200, generate_rpp_response_headers(response)


def _availability(id):
    response = gateways().request_contacts.check(id, client_transaction_id=client_transaction_id())
    if isinstance(response, ErrorResponse):
        raise_registry_error(response)
    return response


@rpp_operation
def requestContacts_availabilityHead(id):
    response = _availability(id)
    headers = generate_rpp_response_headers(response)
    del headers["Content-Type"]  # the OpenAPI defines no content for HEAD
    return None, 200 if response.payload.available else 404, headers


@rpp_operation
def requestContacts_availability(id):
    response = _availability(id)
    return (request_contact_availability.model_to_rpp(response.payload, request_profile().extensions), 200 if response.payload.available else 404,
            generate_rpp_response_headers(response))
