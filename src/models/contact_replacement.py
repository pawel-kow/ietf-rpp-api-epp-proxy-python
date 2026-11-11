from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .address import Address
from .auth_info_intent import AuthInfoIntent
from .localized_postal_info import LocalizedPostalInfo


@dataclass(kw_only=True)
class ContactReplacement:
    """The wanted state of the members of a contact a client may replace. An omitted member is cleared.

    `status` holds client statuses only, the server's are not the client's to replace.
    """
    id: str
    name: Optional[str] = None
    organisationName: Optional[str] = None
    email: Optional[List[str]] = None
    phone: Optional[List[str]] = None
    fax: Optional[List[str]] = None
    address: Optional[Address] = None
    localizedPostalInfo: Optional[LocalizedPostalInfo] = None
    status: List[str] = field(default_factory=list)
    status_reasons: Dict[str, str] = field(default_factory=dict)
    auth_info: AuthInfoIntent = field(default_factory=AuthInfoIntent)
