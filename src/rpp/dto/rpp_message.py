from dataclasses import dataclass
from typing import Optional

from dataclasses_json import Undefined, dataclass_json

from rpp.dto.rpp_object import RPPObject, type_field


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPMessage(RPPObject):
    at_type: str = type_field("message")
    id: Optional[str] = None
    creationDate: Optional[str] = None
    status: Optional[str] = None
    data: Optional[dict] = None
