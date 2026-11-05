from dataclasses import dataclass
from typing import Optional


@dataclass(kw_only=True)
class DomainTransferProcess:
    """The state of the transfer of a domain."""
    name: str
    trStatus: str
    reqClientId: str
    requestDate: str
    actClientId: str
    actionDate: str
    expiryDate: Optional[str] = None
