from dataclasses import dataclass
from typing import Optional

from core.model.contact.address import Address


@dataclass(kw_only=True)
class PostalInfoChange:
    """One postalInfo form of a contact update. `organisationName` "" clears the organisation."""
    form: str
    name: Optional[str] = None
    organisationName: Optional[str] = None
    address: Optional[Address] = None
