from dataclasses import dataclass
from typing import Optional

from dataclasses_json import Undefined, dataclass_json

from rpp.dto.rpp_object import RPPObject, type_field
from rpp.dto.rpp_period import RPPPeriod


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPDomainCreateProcess(RPPObject):
    at_type: str = type_field("domainCreateProcess")
    period: Optional[RPPPeriod] = None
