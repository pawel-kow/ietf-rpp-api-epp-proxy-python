from dataclasses import dataclass
from typing import Optional

from dataclasses_json import dataclass_json, Undefined

from rpp.dto.rpp_object import RPPObject, type_field


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPReviewResponseMessage(RPPObject):
    at_type: str = type_field("reviewResponseMessage")
    objectType: Optional[str] = None
    objectId: Optional[str] = None
    approved: Optional[bool] = None
    clientTransactionId: Optional[str] = None
    serverTransactionId: Optional[str] = None
    completionDate: Optional[str] = None
    message: Optional[str] = None
