from dataclasses import dataclass
from typing import Dict, Optional

from dataclasses_json import Undefined, dataclass_json

from rpp.dto.rpp_object import RPPObject, optional_type_field


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPCardPhone(RPPObject):
    at_type: Optional[str] = optional_type_field()
    number: str
    features: Optional[Dict[str, bool]] = None
