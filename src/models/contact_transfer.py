from dataclasses import dataclass
from typing import Optional

from .common import AuthInfo
from .transfer_operation import TransferOperation


@dataclass(kw_only=True)
class ContactTransfer:
    """One operation on the transfer of a contact."""
    id: str
    operation: TransferOperation
    authInfo: Optional[AuthInfo] = None
