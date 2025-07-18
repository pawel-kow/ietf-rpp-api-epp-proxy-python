from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from typing import List, Optional, Dict
from .rpp_common import RPPProvisioningObject


@dataclass_json
@dataclass
class RPPHostObj:
    name: str

@dataclass_json
@dataclass
class RPPHostAttr:
    name: str
    ipv4: str
    ipv6: str

@dataclass_json
@dataclass
class RPPNS:
    hostObj: Optional[List[RPPHostObj]] = None
    hostAttrs: Optional[List[RPPHostAttr]] = None

@dataclass_json
@dataclass
class RPPContactReference:
    type: List[str]
    value: str

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
    ns: RPPNS = None
    contacts: Optional[List[RPPContactReference]] = None
    dnsSEC: Optional[List[RPPDnsSec]] = None
    processes: RPPProcessMap = None