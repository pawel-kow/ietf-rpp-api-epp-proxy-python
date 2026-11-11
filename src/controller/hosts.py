from connexion import request

import rpp_to_model_mapper as rpp_mapper
from eppclient.epp_hosts import epp_hosts_Check, epp_hosts_Delete, epp_hosts_Info
from flows import create_host, patch_host, replace_host
from models import ErrorResponse
from .auth import get_epp_client
from .helper.rpp_response import (
    client_transaction_id, generate_rpp_response_headers, map_request, raise_epp_error, require_empty_body,
    requested_elements, rpp_operation,
)

OBJECT = "host"


def _host_output(host, requested):
    """The host as a response shows it: with the onDemand data elements the request includes."""
    return rpp_mapper.include_elements.visible(OBJECT, rpp_mapper.hosts.model_to_rpp(host), requested)


def _mutation_response(result, success_status, requested, extra_headers=None):
    """Renders a mutation. Applied but not readable answers 202 with no body."""
    if isinstance(result, ErrorResponse):
        raise_epp_error(result)
    headers = {**generate_rpp_response_headers(result.mutation), **(extra_headers or {})}
    if result.host is None:
        return None, 202, headers
    try:
        return _host_output(result.host, requested), success_status, headers
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
    requested = requested_elements(OBJECT)
    host = map_request(rpp_mapper.hosts.rpp_to_model, body)
    result = create_host(get_epp_client(), host, client_transaction_id())
    return _mutation_response(result, 201, requested, {"Location": f"{str(request.url).rstrip('/')}/{host.name}"})


@rpp_operation
def hosts_read(hostName):
    requested = requested_elements(OBJECT)
    hostresp = epp_hosts_Info(get_epp_client(), hostName, client_transaction_id=client_transaction_id())
    if isinstance(hostresp, ErrorResponse):
        raise_epp_error(hostresp)
    return _host_output(hostresp.host, requested), 200, generate_rpp_response_headers(hostresp)


@rpp_operation
def hosts_update(hostName, body):
    requested = requested_elements(OBJECT)
    wanted = map_request(rpp_mapper.host_replacement.rpp_to_model, hostName, body)
    return _mutation_response(replace_host(get_epp_client(), wanted, client_transaction_id()), 200, requested)


@rpp_operation
def hosts_updatePartial(hostName, body):
    requested = requested_elements(OBJECT)
    update = map_request(rpp_mapper.host_patch.rpp_to_model, hostName, body)

    def wanted_from_current(current):
        return map_request(
            rpp_mapper.host_patch.rpp_to_model_with_current, hostName, body, rpp_mapper.hosts.model_to_rpp(current),
        )

    return _mutation_response(patch_host(get_epp_client(), hostName, update, wanted_from_current, client_transaction_id()), 200, requested)


@rpp_operation
def hosts_delete(hostName):
    require_empty_body()
    hostresp = epp_hosts_Delete(get_epp_client(), hostName, client_transaction_id=client_transaction_id())
    if isinstance(hostresp, ErrorResponse):
        raise_epp_error(hostresp)
    return None, 200, generate_rpp_response_headers(hostresp)
