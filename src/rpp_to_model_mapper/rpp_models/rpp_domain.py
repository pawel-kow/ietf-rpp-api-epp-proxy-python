from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dataclasses_json import Undefined, dataclass_json

from .rpp_object import RPPObject, type_field
from .rpp_auth_info import RPPAuthInfo
from .rpp_contact_reference import RPPContactReference
from .rpp_host_reference import RPPHostReference
from .rpp_labelled_contact import RPPLabelledContact
from .rpp_processes import RPPProcesses
from .rpp_prov_metadata import RPPProvMetadata
from .rpp_status import RPPStatus


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPDomain(RPPObject):
    at_type: str = type_field("domainName")
    name: str
    uName: Optional[str] = None
    lgr: Optional[str] = None
    provMetadata: Optional[RPPProvMetadata] = None
    status: Optional[List[RPPStatus]] = None
    registrant: Optional[RPPContactReference] = None
    contacts: Optional[List[RPPLabelledContact]] = None
    nameservers: Optional[List[RPPHostReference]] = None
    dns: Optional[Dict[str, Any]] = None
    subordinateHosts: Optional[List[RPPHostReference]] = None
    expiryDate: Optional[str] = None
    authInfo: Optional[RPPAuthInfo] = None
    processes: Optional[RPPProcesses] = None
