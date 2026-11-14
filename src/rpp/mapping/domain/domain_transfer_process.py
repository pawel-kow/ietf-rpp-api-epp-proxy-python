from core.capabilities.backend_profile import BackendProfile
from core.model.domain.domain_transfer import DomainTransfer
from core.model.shared.domain_transfer_process import DomainTransferProcess
from core.model.shared.transfer_operation import TransferOperation
from rpp.dto.rpp_domain_transfer_process import RPPDomainTransferProcess
from rpp.dto.rpp_domain_transfer_request import RPPDomainTransferRequest
from rpp.mapping.domain import domains
from rpp.mapping.shared import rpp_authorization
from rpp.mapping.shared.common import parse_rpp, period_duration, PULL, reject_push
from rpp.schema.extensions import added_members
from rpp.schema.validator import validate_schema

SCHEMA = "domainTransferProcess.create"


def _domain_data(name: str, rpp: dict, profile: BackendProfile):
    """The request without the members an offered extension adds to it, and the domain they state: they are members
    of a domain (.spec/spec-rri-extension.md), converted as a create's are. Without such an extension, there is no
    domain, and a domain member stays in the request, where it is undeclared."""
    added = added_members(SCHEMA, profile.extensions)
    if not added:
        return rpp, None
    data = {member: value for member, value in rpp.items() if member in added}
    request = {member: value for member, value in rpp.items() if member not in added}
    return request, domains.rpp_to_model({"@type": "domainName", "name": name, **data}, profile=profile)


def rpp_to_model(name: str, rpp: dict, authorization: str | None, *, profile: BackendProfile) -> DomainTransfer:
    """Converts a transfer request, with the value of its RPP-Authorization header."""
    validate_schema(SCHEMA, rpp, extensions=profile.extensions)
    request, domain = _domain_data(name, rpp, profile)
    request_rpp = parse_rpp(RPPDomainTransferRequest, request)
    reject_push(request_rpp.transferDir, request_rpp.gainingClientId)
    return DomainTransfer(
        name=name,
        operation=TransferOperation.REQUEST,
        authInfo=rpp_authorization.rpp_to_model(authorization),
        duration=period_duration(request_rpp.transferPeriod),
        domain=domain,
    )


def model_to_rpp(process: DomainTransferProcess) -> dict:
    """EPP knows only pull transfers, and its transfer response carries neither id nor period."""
    process_rpp = RPPDomainTransferProcess(
        transferDir=PULL,
        trStatus=process.trStatus,
        reqClientId=process.reqClientId,
        requestDate=process.requestDate,
        actClientId=process.actClientId,
        actionDate=process.actionDate,
        expiryDate=process.expiryDate,
    ).to_rpp()
    validate_schema("domainTransferProcess.read", process_rpp)
    return process_rpp
