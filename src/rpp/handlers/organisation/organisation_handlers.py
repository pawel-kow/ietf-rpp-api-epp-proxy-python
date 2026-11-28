from core.result.error_response import ErrorResponse
from rpp.handlers.shared.requested_elements import requested_elements
from rpp.http.context import get_backend, response_profile
from rpp.http.headers import client_transaction_id, generate_rpp_response_headers
from rpp.http.operation import rpp_operation
from rpp.http.problem import raise_registry_error
from rpp.mapping.organisation import organisations
from rpp.mapping.shared import include_elements

OBJECT = "organisation"


@rpp_operation
def organisations_read(id):
    """The organisation of a registry that publishes them. Create, update, delete, users and processes have no handler (501)."""
    requested = requested_elements(OBJECT)
    resp = get_backend().organisations.info(id, client_transaction_id=client_transaction_id())
    if isinstance(resp, ErrorResponse):
        raise_registry_error(resp)
    output = organisations.model_to_rpp(resp.payload, response_profile().extensions)
    return include_elements.visible(OBJECT, output, requested), 200, generate_rpp_response_headers(resp)
