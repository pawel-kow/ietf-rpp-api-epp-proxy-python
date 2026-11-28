"""The Release Process Object of the rri extension (docs/rri/rri-extension.md): only the Create exists, and it has no
process resource (200 without a Location)."""
from core.result.error_response import ErrorResponse
from extensions.rri.core.flows.release_flows import create_release
from extensions.rri.rpp.mapping import release_process
from rpp.http.context import get_backend, request_profile
from rpp.http.headers import client_transaction_id, generate_rpp_response_headers
from rpp.http.operation import map_request, rpp_operation
from rpp.http.problem import raise_registry_error


@rpp_operation
def domainNameReleaseProcesses_create(name, body):
    keep = map_request(release_process.rpp_to_keep_nameservers, body, request_profile().extensions)
    result = create_release(get_backend(), name, keep, client_transaction_id())
    if isinstance(result, ErrorResponse):
        raise_registry_error(result)
    return (release_process.model_to_rpp(result.stored, request_profile().extensions), 200,
            generate_rpp_response_headers(result.mutation))
