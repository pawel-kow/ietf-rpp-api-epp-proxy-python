from core.model.contact.contact_transfer import ContactTransfer
from core.model.shared.transfer_operation import TransferOperation
from rpp.dto.rpp_transfer_reject import RPPTransferReject
from rpp.mapping.shared import rpp_authorization
from rpp.mapping.shared.common import reject_reason


def rpp_to_model(id: str, rpp: dict | None, authorization: str | None) -> ContactTransfer:
    """Converts a transfer approve, whose content is optional: None for no body. EPP has no reason (data-objects §10.1.1.5)."""
    if rpp is not None:
        reject_reason("transferProcess.transferReject", RPPTransferReject, rpp)
    return ContactTransfer(
        id=id,
        operation=TransferOperation.APPROVE,
        authInfo=rpp_authorization.rpp_to_model(authorization),
    )
