from connexion import request
from flask import current_app
from eppclient.epp_domains import *
from models import *
import flows
import rpp_to_model_mapper as rpp_mapper
from .helper.rpp_response import *
from .auth import get_epp_client

def _idn_tables():
    return current_app.config["RPP_IDN_TABLES"]


OBJECT = "domainName"


def _domain_to_rpp(domain):
    return rpp_mapper.domains.model_to_rpp(domain, _idn_tables())


def _domain_output(domain, requested):
    """The domain as a response shows it: with the onDemand data elements the request includes."""
    return rpp_mapper.include_elements.visible(OBJECT, _domain_to_rpp(domain), requested)


def _domain_after_mutation(domain_name, mutation_resp, success_status, requested, extra_headers=None):
    """Reads the domain back after a mutation the registry has already applied.

    A failed readback must not look like a failed mutation, so it answers 202 with no body.
    """
    headers = {**generate_rpp_response_headers(mutation_resp), **(extra_headers or {})}
    try:
        inforesp = epp_domains_Info(get_epp_client(), domain_name)
        if isinstance(inforesp, ErrorResponse):
            return None, 202, headers
        return _domain_output(inforesp.domain, requested), success_status, headers
    except Exception:
        return None, 202, headers

def _availability(name, u_name, lgr):
    """EPP check has no place for `uName` and `lgr` (draft-obispo-epp-idn-04 adds nothing to it)."""
    map_request(rpp_mapper.domain_availability.rpp_to_model, u_name, lgr)
    ret = epp_domains_Check(get_epp_client(), name, client_transaction_id=client_transaction_id())
    if isinstance(ret, ErrorResponse):
        raise_epp_error(ret)
    return ret

def _updated_domain(result, requested):
    """The answer to an update: the domain as read after it, or 202 when that read failed."""
    if isinstance(result, ErrorResponse):
        raise_epp_error(result)
    headers = generate_rpp_response_headers(result.mutation)
    if result.domain is None:
        return None, 202, headers
    return _domain_output(result.domain, requested), 200, headers


@rpp_operation
def domainNames_availabilityHead(name, uName=None, lgr=None):
    ret = _availability(name, uName, lgr)
    headers = generate_rpp_response_headers(ret)
    del headers["Content-Type"]  # the OpenAPI defines no content for HEAD
    return None, 200 if ret.available else 404, headers

@rpp_operation
def domainNames_availability(name, uName=None, lgr=None):
    ret = _availability(name, uName, lgr)
    return rpp_mapper.domain_availability.model_to_rpp(ret), 200 if ret.available else 404, generate_rpp_response_headers(ret)

@rpp_operation
def domainNames_create(body):
    requested = requested_elements(OBJECT)
    domain = map_request(rpp_mapper.domains.rpp_to_model, body, _idn_tables())
    domainresp = epp_domains_Create(get_epp_client(), domain, client_transaction_id=client_transaction_id())
    if isinstance(domainresp, ErrorResponse):
        raise_epp_error(domainresp)
    location = f"{str(request.url).rstrip('/')}/{domain.name}"
    return _domain_after_mutation(domainresp.domain.name, domainresp, 201, requested, {"Location": location})

@rpp_operation
def domainNames_delete(name):
    require_empty_body()
    domainresp = epp_domains_Delete(get_epp_client(), name, client_transaction_id=client_transaction_id())
    if isinstance(domainresp, ErrorResponse):
        raise_epp_error(domainresp)
    return None, 200, generate_rpp_response_headers(domainresp)

@rpp_operation
def domainNames_read(name):
    requested = requested_elements(OBJECT)
    domainresp = epp_domains_Info(get_epp_client(), name, client_transaction_id=client_transaction_id())
    if isinstance(domainresp, ErrorResponse):
        raise_epp_error(domainresp)
    return _domain_output(domainresp.domain, requested), 200, generate_rpp_response_headers(domainresp)

@rpp_operation
def domainNames_updatePartial(name, body):
    requested = requested_elements(OBJECT)
    update = map_request(rpp_mapper.domain_patch.rpp_to_model, name, body)

    def wanted_from_current(current):
        return map_request(
            rpp_mapper.domain_patch.rpp_to_model_with_current, name, body, _domain_to_rpp(current),
        )

    result = flows.patch_domain(get_epp_client(), name, update, wanted_from_current, client_transaction_id())
    return _updated_domain(result, requested)


@rpp_operation
def domainNames_update(name, body):
    requested = requested_elements(OBJECT)
    wanted = map_request(rpp_mapper.domain_replacement.rpp_to_model, name, body, requested)
    return _updated_domain(flows.replace_domain(get_epp_client(), wanted, client_transaction_id()), requested)


@rpp_operation
def domainNameRenewProcesses_renewCreate(name, body):
    """EPP exposes no renew process, so the answer is a 200 with no Location (core §16.1.4)."""
    renew = map_request(rpp_mapper.domain_renew_process.rpp_to_model, name, body, request.headers.get("RPP-Authorization"))
    resp = flows.renew_domain(get_epp_client(), renew, client_transaction_id())
    if isinstance(resp, ErrorResponse):
        raise_epp_error(resp)
    return rpp_mapper.domain_renew_process.model_to_rpp(resp.renewal), 200, generate_rpp_response_headers(resp)
