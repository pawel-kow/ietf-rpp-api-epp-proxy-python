from models import DomainTransfer, TransferOperation
from rpp_schema_validator import validate_schema
from . import rpp_authorization
from .common import parse_rpp, reject_set
from .rpp_models import RPPDomainTransferReject


def rpp_to_model(name: str, rpp: dict | None, authorization: str | None) -> DomainTransfer:
    """Converts a transfer reject, whose content is optional. EPP has no reason (data-objects §10.1.1.5)."""
    if rpp:  # Connexion passes a missing body as an empty dict
        validate_schema("domainTransferProcess.transferReject", rpp)
        reject_set(reason=parse_rpp(RPPDomainTransferReject, rpp).reason)
    return DomainTransfer(
        name=name,
        operation=TransferOperation.REJECT,
        authInfo=rpp_authorization.rpp_to_model(authorization),
    )
