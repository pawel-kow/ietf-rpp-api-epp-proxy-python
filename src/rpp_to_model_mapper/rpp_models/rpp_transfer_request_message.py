from dataclasses import dataclass
from typing import Optional

from dataclasses_json import Undefined, dataclass_json

from .rpp_object import RPPObject, type_field


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPTransferRequestMessage(RPPObject):
    at_type: str = type_field("transferRequestMessage")
    objectType: Optional[str] = None
    objectId: Optional[str] = None
    status: Optional[str] = None
    requestDate: Optional[str] = None
    actionDate: Optional[str] = None
    process: Optional[dict] = None
