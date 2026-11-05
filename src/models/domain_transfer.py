from dataclasses import dataclass
from typing import Optional

from .common import AuthInfo
from .transfer_operation import TransferOperation


@dataclass(kw_only=True)
class DomainTransfer:
    """One operation on the transfer of a domain."""
    name: str
    operation: TransferOperation
    authInfo: Optional[AuthInfo] = None
    duration: Optional[str] = None
