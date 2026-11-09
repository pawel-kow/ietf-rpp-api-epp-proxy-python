from dataclasses import dataclass
from typing import Optional

from dataclasses_json import Undefined, dataclass_json

from .rpp_object import RPPObject, type_field


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPTransferProcess(RPPObject):
    at_type: str = type_field("transferProcess")
    transferDir: Optional[str] = None
    gainingClientId: Optional[str] = None
    trStatus: Optional[str] = None
    reqClientId: Optional[str] = None
    requestDate: Optional[str] = None
    actClientId: Optional[str] = None
    actionDate: Optional[str] = None
