from dataclasses import dataclass
from typing import Optional

from .contact_transfer_process import ContactTransferProcess
from .domain_transfer_process import DomainTransferProcess


@dataclass(kw_only=True)
class TransferEvent:
    """A transfer reported by a queued message: pending for the losing client, otherwise its outcome."""
    objectType: str
    objectId: str
    trStatus: str
    requestDate: str
    actionDate: str
    expiryDate: Optional[str] = None
    process: Optional[DomainTransferProcess | ContactTransferProcess] = None
