from dataclasses import dataclass
from typing import Optional

from dataclasses_json import dataclass_json, Undefined

from rpp.dto.rpp_auth_info import RPPAuthInfo
from rpp.dto.rpp_object import RPPObject, type_field


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPAuthInfoProcess(RPPObject):
    """The Authorisation Information Process Object of the rri extension (docs/rri/rri-extension.md)."""
    at_type: str = type_field("authInfoProcess")
    authInfo: Optional[RPPAuthInfo] = None
    expiryDate: Optional[str] = None
