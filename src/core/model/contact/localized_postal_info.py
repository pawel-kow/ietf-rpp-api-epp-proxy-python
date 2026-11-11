from dataclasses import dataclass
from typing import Optional

from core.model.contact.address import Address


@dataclass(kw_only=True)
class LocalizedPostalInfo:
    """The localized form of a contact, which is the EPP postalInfo of type 'loc'."""
    name: Optional[str] = None
    organisationName: Optional[str] = None
    address: Optional[Address] = None
