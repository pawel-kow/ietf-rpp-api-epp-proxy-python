from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional

from core.model.contact.address import Address
from core.model.contact.contacts import ContactType
from core.model.contact.localized_postal_info import LocalizedPostalInfo
from core.model.shared.common import AuthInfo


@dataclass(kw_only=True)
class ContactReplacement:
    """The wanted state of the members of a contact a client may replace. An omitted member is cleared.

    `status` holds client statuses only, the server's are not the client's to replace. `unchanged` names the members
    the replacement does not state, which stay as they are stored: a data element with onDemand Visibility the request
    did not include. `type` is the kind the request states, which a backend that holds no kind ignores.
    """
    id: str
    type: Optional[ContactType] = None
    name: Optional[str] = None
    organisationName: Optional[str] = None
    email: Optional[List[str]] = None
    phone: Optional[List[str]] = None
    fax: Optional[List[str]] = None
    address: Optional[Address] = None
    localizedPostalInfo: Optional[LocalizedPostalInfo] = None
    status: List[str] = field(default_factory=list)
    status_reasons: Dict[str, str] = field(default_factory=dict)
    authInfo: Optional[AuthInfo] = None
    unchanged: FrozenSet[str] = frozenset()
