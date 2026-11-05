from dataclasses import dataclass
from typing import Optional

from dataclasses_json import Undefined, dataclass_json

from .rpp_object import RPPObject, optional_type_field


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPCardAddressComponent(RPPObject):
    at_type: Optional[str] = optional_type_field()
    kind: str
    value: str
