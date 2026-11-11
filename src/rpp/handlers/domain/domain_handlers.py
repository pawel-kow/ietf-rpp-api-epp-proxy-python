from connexion import ProblemException, request

from core.flows.domain.domain_flows import (
    create_domain, patch_domain, read_domain_restore, renew_domain, replace_domain,
)
from core.result.error_response import ErrorResponse
from rpp.handlers.shared.requested_elements import requested_elements
from rpp.http.context import backend_profile, get_backend
from rpp.http.headers import client_transaction_id, generate_rpp_response_headers
from rpp.http.operation import map_request, require_empty_body, rpp_operation
from rpp.http.problem import raise_registry_error
from rpp.mapping.domain import (
    domain_availability, domain_patch, domain_renew_process, domain_replacement, domain_restore_patch,
    domain_restore_process, domain_restore_report, domains,
)
from rpp.mapping.shared import include_elements

OBJECT = "domainName"


def _domain_output(domain, requested):
    """The domain as a response shows it: with the onDemand data elements the request includes."""
    return include_elements.visible(OBJECT, domains.model_to_rpp(domain), requested)


def _mutation_answer(result, requested, status=200, extra_headers=None):
    """The answer to a mutation: the domain as read after it, or 202 with no body when that read failed."""
    if isinstance(result, ErrorResponse):
        raise_registry_error(result)
    headers = {**generate_rpp_response_headers(result.mutation), **(extra_headers or {})}
    if result.stored is None:
        return None, 202, headers
    return _domain_output(result.stored, requested), status, headers


def _availability(name, u_name, lgr):
    """EPP check has no place for `uName` and `lgr` (draft-obispo-epp-idn-04 adds nothing to it)."""
    map_request(domain_availability.rpp_to_model, u_name, lgr)
    ret = get_backend().domains.check(name, client_transaction_id=client_transaction_id())
    if isinstance(ret, ErrorResponse):
        raise_registry_error(ret)
    return ret

@rpp_operation
def domainNames_availabilityHead(name, uName=None, lgr=None):
    ret = _availability(name, uName, lgr)
    headers = generate_rpp_response_headers(ret)
    del headers["Content-Type"]  # the OpenAPI defines no content for HEAD
    return None, 200 if ret.payload.available else 404, headers

@rpp_operation
def domainNames_availability(name, uName=None, lgr=None):
    ret = _availability(name, uName, lgr)
    return domain_availability.model_to_rpp(ret.payload), 200 if ret.payload.available else 404, generate_rpp_response_headers(ret)

@rpp_operation
def domainNames_create(body):
    requested = requested_elements(OBJECT)
    domain = map_request(domains.rpp_to_model, body, profile=backend_profile())
    result = create_domain(get_backend(), domain, client_transaction_id())
    location = {"Location": f"{str(request.url).rstrip('/')}/{domain.name}"}
    try:
        return _mutation_answer(result, requested, 201, location)
    except ProblemException:
        raise
    except Exception:
        # The domain is created: a read-back that cannot be shown must not look like a failed create.
        return None, 202, {**generate_rpp_response_headers(result.mutation), **location}

@rpp_operation
def domainNames_delete(name):
    require_empty_body()
    domainresp = get_backend().domains.delete(name, client_transaction_id=client_transaction_id())
    if isinstance(domainresp, ErrorResponse):
        raise_registry_error(domainresp)
    return None, 200, generate_rpp_response_headers(domainresp)

@rpp_operation
def domainNames_read(name):
    requested = requested_elements(OBJECT)
    domainresp = get_backend().domains.info(name, client_transaction_id=client_transaction_id())
    if isinstance(domainresp, ErrorResponse):
        raise_registry_error(domainresp)
    return _domain_output(domainresp.payload, requested), 200, generate_rpp_response_headers(domainresp)

@rpp_operation
def domainNames_updatePartial(name, body):
    requested = requested_elements(OBJECT)
    update = map_request(domain_patch.rpp_to_model, name, body, profile=backend_profile())

    def wanted_from_current(current):
        return map_request(
            domain_patch.rpp_to_model_with_current, name, body, domains.model_to_rpp(current),
            profile=backend_profile(),
        )

    result = patch_domain(get_backend(), name, update, wanted_from_current, client_transaction_id())
    return _mutation_answer(result, requested)


@rpp_operation
def domainNames_update(name, body):
    requested = requested_elements(OBJECT)
    wanted = map_request(domain_replacement.rpp_to_model, name, body, requested, profile=backend_profile())
    return _mutation_answer(replace_domain(get_backend(), wanted, client_transaction_id()), requested)


@rpp_operation
def domainNameRenewProcesses_renewCreate(name, body):
    """EPP exposes no renew process, so the answer is a 200 with no Location (core §16.1.4)."""
    renew = map_request(domain_renew_process.rpp_to_model, name, body, request.headers.get("RPP-Authorization"))
    resp = renew_domain(get_backend(), renew, client_transaction_id())
    if isinstance(resp, ErrorResponse):
        raise_registry_error(resp)
    return domain_renew_process.model_to_rpp(resp.payload), 200, generate_rpp_response_headers(resp)


def _restore(restore):
    resp = get_backend().domains.restore(restore, client_transaction_id=client_transaction_id())
    if isinstance(resp, ErrorResponse):
        raise_registry_error(resp)
    return domain_restore_process.model_to_rpp(resp.payload), 200, generate_rpp_response_headers(resp)


@rpp_operation
def domainNameRestoreProcesses_create(name, body):
    """EPP exposes no restore process, so the answer is a 200 with no Location (core §16.1.4)."""
    return _restore(map_request(domain_restore_process.rpp_to_model, name, body))


@rpp_operation
def domainNameRestoreProcesses_update(name, body):
    return _restore(map_request(domain_restore_report.rpp_to_model, name, body))


@rpp_operation
def domainNameRestoreProcesses_updatePartial(name, body):
    return _restore(map_request(domain_restore_patch.rpp_to_model, name, body))


@rpp_operation
def domainNameRestoreProcesses_read(name):
    resp = read_domain_restore(get_backend(), name, client_transaction_id())
    if isinstance(resp, ErrorResponse):
        raise_registry_error(resp)
    return domain_restore_process.model_to_rpp(resp.payload), 200, generate_rpp_response_headers(resp)
