"""The Authorisation Information Issue Process Object of the rri extension (docs/rri/rri-extension.md)."""
from core.result.error_response import ErrorResponse
from extensions.rri.core.flows.auth_info_issue_flows import create_auth_info_issue
from extensions.rri.rpp.mapping import auth_info_issue_process
from rpp.http.context import get_backend, request_profile
from rpp.http.headers import client_transaction_id, generate_rpp_response_headers
from rpp.http.operation import map_request, rpp_operation
from rpp.http.problem import raise_registry_error


@rpp_operation
def domainNameAuthInfoIssueProcesses_create(name, body):
    map_request(auth_info_issue_process.check_request, body, request_profile().extensions)
    response = create_auth_info_issue(get_backend(), name, client_transaction_id())
    if isinstance(response, ErrorResponse):
        raise_registry_error(response)
    return (auth_info_issue_process.model_to_rpp(request_profile().extensions), 200,
            generate_rpp_response_headers(response))
