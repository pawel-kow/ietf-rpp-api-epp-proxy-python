from core.model.domain.domain_transfer import DomainTransfer
from core.model.shared.transfer_operation import TransferOperation
from rpp.dto.rpp_domain_transfer_reject import RPPDomainTransferReject
from rpp.mapping.shared import rpp_authorization
from rpp.mapping.shared.common import reject_reason


def rpp_to_model(name: str, rpp: dict | None, authorization: str | None) -> DomainTransfer:
    """Converts a transfer reject, whose content is optional. EPP has no reason (data-objects §10.1.1.5)."""
    if rpp:  # Connexion passes a missing body as an empty dict
        reject_reason("domainTransferProcess.transferReject", RPPDomainTransferReject, rpp)
    return DomainTransfer(
        name=name,
        operation=TransferOperation.REJECT,
        authInfo=rpp_authorization.rpp_to_model(authorization),
    )
