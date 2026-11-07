from dataclasses import dataclass
from typing import Optional

from dataclasses_json import Undefined, dataclass_json

from .rpp_object import RPPObject, type_field
from .rpp_period import RPPPeriod


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPDomainTransferRequest(RPPObject):
    """What a client may send to request a transfer: the members that are not read-only."""
    at_type: str = type_field("domainTransferProcess")
    transferDir: Optional[str] = None
    gainingClientId: Optional[str] = None
    transferPeriod: Optional[RPPPeriod] = None
