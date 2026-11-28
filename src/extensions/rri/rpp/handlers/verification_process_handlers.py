"""The Verification Process Object of the rri extension (docs/rri/rri-extension.md), at the path of a domain name's
processes `create_app` adds where the backend profile offers it. It is only read; the other operations have no handler (501)."""
from connexion import request

from core.result.error_response import ErrorResponse
from extensions.rri.core.flows.verification_process_flows import read_verification_process
from extensions.rri.rpp.mapping import verification_process
from rpp.http.context import get_backend, response_profile
from rpp.http.headers import client_transaction_id, generate_rpp_response_headers
from rpp.http.operation import map_request, rpp_operation
from rpp.http.problem import raise_registry_error
from rpp.mapping.shared import rpp_authorization


@rpp_operation
def domainNameVerificationProcesses_read(name):
    authorization = map_request(rpp_authorization.rpp_to_model, request.headers.get("RPP-Authorization"))
    response = read_verification_process(get_backend(), name, authorization, client_transaction_id())
    if isinstance(response, ErrorResponse):
        raise_registry_error(response)
    return (verification_process.model_to_rpp(response.payload, response_profile().extensions), 200,
            generate_rpp_response_headers(response))
