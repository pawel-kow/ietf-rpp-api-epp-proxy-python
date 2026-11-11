from dataclasses import dataclass
from typing import Optional

from dataclasses_json import dataclass_json, Undefined

from rpp.dto.rpp_object import RPPObject, type_field


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPTransferOutcomeMessage(RPPObject):
    at_type: str = type_field("transferOutcomeMessage")
    objectType: Optional[str] = None
    objectId: Optional[str] = None
    trStatus: Optional[str] = None
    requestDate: Optional[str] = None
    actionDate: Optional[str] = None
    expiryDate: Optional[str] = None
    process: Optional[dict] = None
