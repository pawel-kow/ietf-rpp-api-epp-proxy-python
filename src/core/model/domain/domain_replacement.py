from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional

from core.model.shared.common import AuthInfo
from core.model.domain.dns_sec import DnsSec
from core.model.domain.domains import ContactReferenceNew, NS


@dataclass(kw_only=True)
class DomainReplacement:
    """The wanted state of the members of a domain a client may replace. An omitted member is cleared.

    `ns` holds host objects or host attributes, not both. `contacts` are the roles other than the registrant.
    `status` holds client statuses only, the server's are not the client's to replace. `unchanged` names the members
    the replacement does not state, which stay as they are stored: a data element with onDemand Visibility the request
    did not include.
    """
    name: str
    ns: Optional[NS] = None
    registrant: Optional[str] = None
    contacts: List[ContactReferenceNew] = field(default_factory=list)
    dnsSEC: Optional[DnsSec] = None
    status: List[str] = field(default_factory=list)
    status_reasons: Dict[str, str] = field(default_factory=dict)
    authInfo: Optional[AuthInfo] = None
    unchanged: FrozenSet[str] = frozenset()
