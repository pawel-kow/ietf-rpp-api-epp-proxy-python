from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dataclasses_json import Undefined, dataclass_json

from .rpp_object import RPPObject, type_field
from .rpp_auth_info import RPPAuthInfo
from .rpp_card import RPPCard
from .rpp_prov_metadata import RPPProvMetadata
from .rpp_status import RPPStatus


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPContact(RPPObject):
    at_type: str = type_field("contact")
    id: str
    contactInfo: RPPCard
    provMetadata: Optional[RPPProvMetadata] = None
    status: Optional[List[RPPStatus]] = None
    authInfo: Optional[RPPAuthInfo] = None
    disclose: Optional[Dict[str, Any]] = None
