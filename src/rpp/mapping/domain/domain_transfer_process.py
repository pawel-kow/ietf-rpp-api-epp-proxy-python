from core.model.domain.domain_transfer import DomainTransfer
from core.model.shared.domain_transfer_process import DomainTransferProcess
from core.model.shared.transfer_operation import TransferOperation
from rpp.dto.rpp_domain_transfer_process import RPPDomainTransferProcess
from rpp.dto.rpp_domain_transfer_request import RPPDomainTransferRequest
from rpp.mapping.shared import rpp_authorization
from rpp.mapping.shared.common import parse_rpp, period_duration, PULL, reject_push
from rpp.schema.validator import validate_schema


def rpp_to_model(name: str, rpp: dict, authorization: str | None) -> DomainTransfer:
    """Converts a transfer request, with the value of its RPP-Authorization header."""
    validate_schema("domainTransferProcess.create", rpp)
    request_rpp = parse_rpp(RPPDomainTransferRequest, rpp)
    reject_push(request_rpp.transferDir, request_rpp.gainingClientId)
    return DomainTransfer(
        name=name,
        operation=TransferOperation.REQUEST,
        authInfo=rpp_authorization.rpp_to_model(authorization),
        duration=period_duration(request_rpp.transferPeriod),
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
