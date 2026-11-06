from connexion import request

import rpp_to_model_mapper as rpp_mapper
from eppclient.epp_hosts import epp_hosts_Check, epp_hosts_Delete, epp_hosts_Info
from flows import create_host, patch_host, replace_host
from models import ErrorResponse
from .auth import get_epp_client
from .helper.rpp_response import (
    client_transaction_id, generate_rpp_response_headers, map_request, raise_epp_error, require_empty_body,
    rpp_operation,
)


def _mutation_response(result, success_status, extra_headers=None):
    """Renders a mutation. Applied but not readable answers 202 with no body."""
    if isinstance(result, ErrorResponse):
        raise_epp_error(result)
    headers = {**generate_rpp_response_headers(result.mutation), **(extra_headers or {})}
    if result.host is None:
        return None, 202, headers
    try:
        return rpp_mapper.hosts.model_to_rpp(result.host), success_status, headers
    except Exception:
        return None, 202, headers


def _availability(host_name):
    ret = epp_hosts_Check(get_epp_client(), host_name, client_transaction_id=client_transaction_id())
    if isinstance(ret, ErrorResponse):
        raise_epp_error(ret)
    return ret


@rpp_operation
def hosts_availabilityHead(hostName):
    ret = _availability(hostName)
    headers = generate_rpp_response_headers(ret)
    del headers["Content-Type"]  # the OpenAPI defines no content for HEAD
    return None, 200 if ret.available else 404, headers


@rpp_operation
def hosts_availability(hostName):
    ret = _availability(hostName)
    return rpp_mapper.host_availability.model_to_rpp(ret), 200 if ret.available else 404, generate_rpp_response_headers(ret)


@rpp_operation
def hosts_create(body):
    host = map_request(rpp_mapper.hosts.rpp_to_model, body)
    result = create_host(get_epp_client(), host, client_transaction_id())
    return _mutation_response(result, 201, {"Location": f"{str(request.url).rstrip('/')}/{host.name}"})


@rpp_operation
def hosts_read(hostName):
    hostresp = epp_hosts_Info(get_epp_client(), hostName, client_transaction_id=client_transaction_id())
    if isinstance(hostresp, ErrorResponse):
        raise_epp_error(hostresp)
    return rpp_mapper.hosts.model_to_rpp(hostresp.host), 200, generate_rpp_response_headers(hostresp)


@rpp_operation
def hosts_update(hostName, body):
    wanted = map_request(rpp_mapper.host_replacement.rpp_to_model, body)
    return _mutation_response(replace_host(get_epp_client(), hostName, wanted, client_transaction_id()), 200)


@rpp_operation
def hosts_updatePartial(hostName, body):
    update = map_request(rpp_mapper.host_patch.rpp_to_model, hostName, body)

    def wanted_from_current(current):
        return map_request(
            rpp_mapper.host_patch.rpp_to_model_with_current, hostName, body, rpp_mapper.hosts.model_to_rpp(current),
        )

    return _mutation_response(patch_host(get_epp_client(), hostName, update, wanted_from_current, client_transaction_id()), 200)


@rpp_operation
def hosts_delete(hostName):
    require_empty_body()
    hostresp = epp_hosts_Delete(get_epp_client(), hostName, client_transaction_id=client_transaction_id())
    if isinstance(hostresp, ErrorResponse):
        raise_epp_error(hostresp)
    return None, 200, generate_rpp_response_headers(hostresp)
