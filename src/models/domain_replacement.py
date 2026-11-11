from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .auth_info_intent import AuthInfoIntent
from .dns_sec import DnsSec
from .domains import ContactReferenceNew, NS


@dataclass(kw_only=True)
class DomainReplacement:
    """The wanted state of the members of a domain a client may replace. An omitted member is cleared.

    `ns` holds host objects or host attributes, not both. `contacts` are the roles other than the registrant.
    `status` holds client statuses only, the server's are not the client's to replace.
    """
    name: str
    ns: Optional[NS] = None
    registrant: Optional[str] = None
    contacts: List[ContactReferenceNew] = field(default_factory=list)
    dnsSEC: Optional[DnsSec] = None
    status: List[str] = field(default_factory=list)
    status_reasons: Dict[str, str] = field(default_factory=dict)
    auth_info: AuthInfoIntent = field(default_factory=AuthInfoIntent)
