from core.model.domain.domain_transfer import DomainTransfer
from core.model.shared.transfer_operation import TransferOperation
from . import rpp_authorization
from .common import reject_reason
from .rpp_models import RPPDomainTransferReject


def rpp_to_model(name: str, rpp: dict | None, authorization: str | None) -> DomainTransfer:
    """Converts a transfer approve, whose content is optional: None for no body. EPP has no reason (data-objects §10.1.1.5)."""
    if rpp is not None:
        reject_reason("domainTransferProcess.transferReject", RPPDomainTransferReject, rpp)
    return DomainTransfer(
        name=name,
        operation=TransferOperation.APPROVE,
        authInfo=rpp_authorization.rpp_to_model(authorization),
    )
