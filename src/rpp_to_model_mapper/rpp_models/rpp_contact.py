from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from typing import List, Optional, Dict
from .rpp_common import RPPProvisioningObject
from enum import Enum

@dataclass_json
@dataclass(kw_only=True)
class RPPAddress:
    street: Optional[List[str]] = None
    city: Optional[str] = None
    stateProvince: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = None

class RPPContactType(Enum):
    PERSON = "PERSON"
    ORG = "ORG"

@dataclass_json
@dataclass(kw_only=True)
class RPPContact(RPPProvisioningObject):
    id: str;
    contactType: RPPContactType
    name: Optional[str] = None;
    organisationName: Optional[str] = None;
    email: Optional[List[str]] = None;
    phone: Optional[List[str]] = None;
    fax: Optional[List[str]] = None;
    address: Optional[RPPAddress] = None;
