from dataclasses import dataclass
from typing import Optional

from dataclasses_json import dataclass_json, Undefined

from rpp.dto.rpp_object import optional_type_field, RPPObject


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPCardAddressComponent(RPPObject):
    at_type: Optional[str] = optional_type_field()
    kind: str
    value: str
