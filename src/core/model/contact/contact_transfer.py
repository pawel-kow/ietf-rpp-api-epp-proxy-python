from dataclasses import dataclass
from typing import Optional

from core.model.shared.common import AuthInfo
from core.model.shared.transfer_operation import TransferOperation


@dataclass(kw_only=True)
class ContactTransfer:
    """One operation on the transfer of a contact."""
    id: str
    operation: TransferOperation
    authInfo: Optional[AuthInfo] = None
