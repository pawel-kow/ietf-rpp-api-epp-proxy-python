from connexion import request
from eppclient.epp_domains import *
from models import *
import flows
import rpp_to_model_mapper as rpp_mapper
from .helper.rpp_response import *
from .auth import get_epp_client

def _domain_after_mutation(domain_name, mutation_resp, success_status, extra_headers=None):
    """Reads the domain back after a mutation the registry has already applied.

    A failed readback must not look like a failed mutation, so it answers 202 with no body.
    """
    headers = {**generate_rpp_response_headers(mutation_resp), **(extra_headers or {})}
    try:
        inforesp = epp_domains_Info(get_epp_client(), domain_name)
        if isinstance(inforesp, ErrorResponse):
            return None, 202, headers
        return rpp_mapper.domains.model_to_rpp(inforesp.domain), success_status, headers
    except Exception:
        return None, 202, headers

def _availability(name):
    ret = epp_domains_Check(get_epp_client(), name, client_transaction_id=client_transaction_id())
    if isinstance(ret, ErrorResponse):
        raise_epp_error(ret)
    return ret

@rpp_operation
def domainNames_availabilityHead(name):
    ret = _availability(name)
    headers = generate_rpp_response_headers(ret)
    del headers["Content-Type"]  # the OpenAPI defines no content for HEAD
    return None, 200 if ret.available else 404, headers

@rpp_operation
def domainNames_availability(name):
    ret = _availability(name)
    return rpp_mapper.domain_availability.model_to_rpp(ret), 200 if ret.available else 404, generate_rpp_response_headers(ret)

@rpp_operation
def domainNames_create(body):
    domain = map_request(rpp_mapper.domains.rpp_to_model, body)
    domainresp = epp_domains_Create(get_epp_client(), domain, client_transaction_id=client_transaction_id())
    if isinstance(domainresp, ErrorResponse):
        raise_epp_error(domainresp)
    location = f"{str(request.url).rstrip('/')}/{domain.name}"
    return _domain_after_mutation(domainresp.domain.name, domainresp, 201, {"Location": location})

@rpp_operation
def domainNames_delete(name):
    require_empty_body()
    domainresp = epp_domains_Delete(get_epp_client(), name, client_transaction_id=client_transaction_id())
    if isinstance(domainresp, ErrorResponse):
        raise_epp_error(domainresp)
    return None, 200, generate_rpp_response_headers(domainresp)

@rpp_operation
def domainNames_read(name):
    domainresp = epp_domains_Info(get_epp_client(), name, client_transaction_id=client_transaction_id())
    if isinstance(domainresp, ErrorResponse):
        raise_epp_error(domainresp)
    return rpp_mapper.domains.model_to_rpp(domainresp.domain), 200, generate_rpp_response_headers(domainresp)

@rpp_operation
def domainNames_updatePartial(name, body):
    update = map_request(rpp_mapper.domain_patch.rpp_to_model, name, body)

    def update_from_current(current):
        return map_request(
            rpp_mapper.domain_patch.rpp_to_model_with_current, name, body, rpp_mapper.domains.model_to_rpp(current),
        )

    result = flows.patch_domain(get_epp_client(), name, update, update_from_current, client_transaction_id())
    if isinstance(result, ErrorResponse):
        raise_epp_error(result)
    headers = generate_rpp_response_headers(result.mutation)
    if result.domain is None:
        return None, 202, headers
    return rpp_mapper.domains.model_to_rpp(result.domain), 200, headers

@rpp_operation
def domainNameRenewProcesses_renewCreate(name, body):
    """EPP exposes no renew process, so the answer is a 200 with no Location (core §16.1.4)."""
    renew = map_request(rpp_mapper.domain_renew_process.rpp_to_model, name, body)
    resp = flows.renew_domain(get_epp_client(), renew, client_transaction_id())
    if isinstance(resp, ErrorResponse):
        raise_epp_error(resp)
    return rpp_mapper.domain_renew_process.model_to_rpp(resp.renewal), 200, generate_rpp_response_headers(resp)
