from dataclasses import dataclass
from typing import Optional

from dataclasses_json import dataclass_json, Undefined

from rpp.dto.rpp_object import RPPObject, type_field


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPContactAvailability(RPPObject):
    at_type: str = type_field("contactAvailability")
    available: bool
    reason: Optional[str] = None
