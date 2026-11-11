from dataclasses import dataclass
from typing import Optional

from dataclasses_json import dataclass_json, Undefined

from rpp.dto.rpp_object import RPPObject, type_field
from rpp.dto.rpp_period import RPPPeriod


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPDomainRenewProcess(RPPObject):
    at_type: str = type_field("renewProcess")
    expiryDate: Optional[str] = None
    renewalPeriod: Optional[RPPPeriod] = None
