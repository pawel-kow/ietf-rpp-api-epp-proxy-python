from connexion import request, ProblemException
from eppclient.epp_domains import *
from models import *
from rpp_to_model_mapper import *
from .helper.rpp_response import *
import asyncio
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
        return domain_to_rpp(inforesp.domain), success_status, headers
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
    return domain_availability_to_rpp(ret), 200 if ret.available else 404, generate_rpp_response_headers(ret)

@rpp_operation
def domainNames_create(body):
    domain = map_request(rpp_to_domain, body)
    domainresp = epp_domains_Create(get_epp_client(), domain, client_transaction_id=client_transaction_id())
    if isinstance(domainresp, ErrorResponse):
        raise_epp_error(domainresp)
    location = f"{str(request.url).rstrip('/')}/{domain.name}"
    return _domain_after_mutation(domainresp.domain.name, domainresp, 201, {"Location": location})

@rpp_operation
def domainNames_delete(name):
    if asyncio.run(request.get_body()):
        raise ProblemException(status=400, title="Bad Request", detail="Request body must be empty for DELETE method")
    domainresp = epp_domains_Delete(get_epp_client(), name, client_transaction_id=client_transaction_id())
    if isinstance(domainresp, ErrorResponse):
        raise_epp_error(domainresp)
    return None, 200, generate_rpp_response_headers(domainresp)

@rpp_operation
def domainNames_read(name):
    domainresp = epp_domains_Info(get_epp_client(), name, client_transaction_id=client_transaction_id())
    if isinstance(domainresp, ErrorResponse):
        raise_epp_error(domainresp)
    return domain_to_rpp(domainresp.domain), 200, generate_rpp_response_headers(domainresp)

@rpp_operation
def domainNames_updatePartial(name, body):
    domain_update = map_request(rpp_to_domain_update, name, body)
    domainresp = epp_domains_Update(get_epp_client(), domain_update, client_transaction_id=client_transaction_id())
    if isinstance(domainresp, ErrorResponse):
        raise_epp_error(domainresp)
    return _domain_after_mutation(name, domainresp, 200)
