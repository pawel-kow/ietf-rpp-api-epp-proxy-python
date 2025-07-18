from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from typing import List, Optional, Dict

@dataclass_json
@dataclass
class RPPAuthInfo:
    pw: Optional[str] = None
    hash: Optional[str] = None

@dataclass_json
@dataclass(kw_only=True)
class RPPProvisioningObject:
    status: Optional[List[str]] = None
    crDate: Optional[str] = None
    exDate: Optional[str] = None
    upDate: Optional[str] = None
    trDate: Optional[str] = None
    clID: Optional[str] = None
    crID: Optional[str] = None
    authInfo: Optional[RPPAuthInfo] = None
