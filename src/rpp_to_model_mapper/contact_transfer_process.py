from models import ContactTransfer, ContactTransferProcess, TransferOperation
from rpp_schema_validator import validate_schema
from . import rpp_authorization
from .common import parse_rpp, reject_set
from .not_supported_by_epp import NotSupportedByEpp
from .rpp_models import RPPTransferProcess

PULL = "pull"


def rpp_to_model(id: str, rpp: dict, authorization: str | None) -> ContactTransfer:
    """Converts a transfer request, with the value of its RPP-Authorization header."""
    validate_schema("transferProcess.create", rpp)
    process_rpp = parse_rpp(RPPTransferProcess, rpp)
    if process_rpp.transferDir not in (None, PULL):
        raise NotSupportedByEpp(f"Transfer direction '{process_rpp.transferDir}'")
    reject_set(gainingClientId=process_rpp.gainingClientId)
    return ContactTransfer(
        id=id,
        operation=TransferOperation.REQUEST,
        authInfo=rpp_authorization.rpp_to_model(authorization),
    )


def model_to_rpp(process: ContactTransferProcess) -> dict:
    """EPP knows only pull transfers, and its transfer response carries neither id nor period."""
    process_rpp = RPPTransferProcess(
        transferDir=PULL,
        trStatus=process.trStatus,
        reqClientId=process.reqClientId,
        requestDate=process.requestDate,
        actClientId=process.actClientId,
        actionDate=process.actionDate,
    ).to_rpp()
    validate_schema("transferProcess.read", process_rpp)
    return process_rpp
