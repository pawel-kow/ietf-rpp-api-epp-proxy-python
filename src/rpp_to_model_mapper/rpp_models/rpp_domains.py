from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from typing import List, Optional, Dict
from .rpp_common import RPPAuthInfo, RPPProvisioningObject
from .rpp_contact import RPPContactMinimal


@dataclass_json
@dataclass
class RPPHostObj:
    name: str


@dataclass_json
@dataclass
class RPPAddr:
    ipv4: Optional[List[str]] = None
    ipv6: Optional[List[str]] = None

@dataclass_json
@dataclass
class RPPHostAttr:
    name: str
    addr: Optional[RPPAddr] = None

@dataclass_json
@dataclass
class RPPNS:
    hostObj: Optional[List[RPPHostObj]] = None
    hostAttr: Optional[List[RPPHostAttr]] = None

@dataclass_json
@dataclass
class RPPContactReference:
    type: List[str]
    value: str

@dataclass_json
@dataclass
class RPPContactReferenceNew:
    type: str
    object: RPPContactMinimal

@dataclass_json
@dataclass
class RPPDnsSec:
    # Add DNSSEC properties here if needed
    pass

@dataclass_json
@dataclass
class RPPProcess:
    pass

@dataclass_json
@dataclass
class RPPCreationProcess(RPPProcess):
    period: Optional[str] = None

@dataclass_json
@dataclass
class RPPRenewalProcess(RPPProcess):
    period: Optional[str] = None

@dataclass_json
@dataclass
class RPPTransferProcess(RPPProcess):
    period: Optional[str] = None

@dataclass_json
@dataclass
class RPPProcessMap:
    creation: Optional[RPPCreationProcess] = None
    renewal: Optional[RPPRenewalProcess] = None
    transfer: Optional[RPPTransferProcess] = None
    
@dataclass_json
@dataclass
class RPPDomain(RPPProvisioningObject):
    name: str
    ns: Optional[RPPNS] = None
    contacts: Optional[List[RPPContactReference]] = None
    dnsSEC: Optional[List[RPPDnsSec]] = None
    processes: Optional[RPPProcessMap] = None
    
@dataclass_json
@dataclass
class RPPDomainUpdateAdd:
    ns: Optional[RPPNS] = None
    contacts: Optional[List[RPPContactReferenceNew]] = None
    dnsSEC: Optional[List[RPPDnsSec]] = None

@dataclass_json
@dataclass
class RPPDomainUpdateRemove:
    ns: Optional[RPPNS] = None
    contacts: Optional[List[RPPContactReferenceNew]] = None
    dnsSEC: Optional[List[RPPDnsSec]] = None

@dataclass_json
@dataclass
class RPPDomainUpdateChange:
    authInfo: Optional[RPPAuthInfo] = None
    
@dataclass_json
@dataclass
class RPPDomainUpdate:
    add: Optional[RPPDomainUpdateAdd] = None
    remove: Optional[RPPDomainUpdateRemove] = None
    update: Optional[RPPDomainUpdateChange] = None