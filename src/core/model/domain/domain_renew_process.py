from dataclasses import dataclass
from typing import Optional


@dataclass(kw_only=True)
class DomainRenewProcess:
    """The outcome of a renewal. `expiryDate` is None when the registry did not report it."""
    name: Optional[str] = None
    expiryDate: Optional[str] = None
