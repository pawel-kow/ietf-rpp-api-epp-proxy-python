from dataclasses import dataclass
from typing import Optional

from dataclasses_json import Undefined, dataclass_json

from rpp.dto.rpp_object import RPPObject, type_field


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPHostReference(RPPObject):
    at_type: str = type_field("host")
    hostName: str
