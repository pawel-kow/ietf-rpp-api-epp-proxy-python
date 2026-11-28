"""The Authorisation Information Process Object of the rri extension (docs/rri/rri-extension.md), at the paths of a
domain name's processes `create_app` adds where the backend profile offers it."""
from core.result.error_response import ErrorResponse
from extensions.rri.core.flows.auth_info_process_flows import (
    create_auth_info_process, delete_auth_info_process, read_auth_info_process,
)
from extensions.rri.rpp.mapping import auth_info_process
from rpp.http.context import get_backend, request_profile
from rpp.http.headers import client_transaction_id, generate_rpp_response_headers
from rpp.http.operation import map_request, require_empty_body, rpp_operation
from rpp.http.problem import raise_registry_error


@rpp_operation
def domainNameAuthInfoProcesses_create(name, body):
    setting = map_request(auth_info_process.rpp_to_model, name, body, request_profile().extensions)
    result = create_auth_info_process(get_backend(), setting, client_transaction_id())
    if isinstance(result, ErrorResponse):
        raise_registry_error(result)
    return (auth_info_process.model_to_rpp(result.stored, request_profile().extensions), 200,
            generate_rpp_response_headers(result.mutation))


@rpp_operation
def domainNameAuthInfoProcesses_read(name):
    response = read_auth_info_process(get_backend(), name, client_transaction_id())
    if isinstance(response, ErrorResponse):
        raise_registry_error(response)
    return (auth_info_process.model_to_rpp(response.payload, request_profile().extensions), 200,
            generate_rpp_response_headers(response))


@rpp_operation
def domainNameAuthInfoProcesses_delete(name):
    require_empty_body()
    response = delete_auth_info_process(get_backend(), name, client_transaction_id())
    if isinstance(response, ErrorResponse):
        raise_registry_error(response)
    return None, 200, generate_rpp_response_headers(response)
