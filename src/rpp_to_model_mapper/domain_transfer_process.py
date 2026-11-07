from models import DomainTransfer, DomainTransferProcess, TransferOperation
from rpp_schema_validator import validate_schema
from . import rpp_authorization
from .common import PULL, parse_rpp, period_duration, reject_push
from .rpp_models import RPPDomainTransferProcess, RPPDomainTransferRequest


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
