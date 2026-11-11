from core.model.contact.contact_transfer import ContactTransfer
from core.model.shared.transfer_operation import TransferOperation
from . import rpp_authorization
from .common import reject_reason
from .rpp_models import RPPTransferReject


def rpp_to_model(id: str, rpp: dict | None, authorization: str | None) -> ContactTransfer:
    """Converts a transfer reject, whose content is optional. EPP has no reason (data-objects §10.1.1.5)."""
    if rpp:  # Connexion passes a missing body as an empty dict
        reject_reason("transferProcess.transferReject", RPPTransferReject, rpp)
    return ContactTransfer(
        id=id,
        operation=TransferOperation.REJECT,
        authInfo=rpp_authorization.rpp_to_model(authorization),
    )
