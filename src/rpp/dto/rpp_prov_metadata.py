from dataclasses import dataclass
from typing import Optional

from dataclasses_json import Undefined, dataclass_json

from rpp.dto.rpp_object import RPPObject, type_field


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPProvMetadata(RPPObject):
    at_type: str = type_field("provMetadata")
    spClientId: str
    repositoryId: Optional[str] = None
    crClientId: Optional[str] = None
    crDate: Optional[str] = None
    upClientId: Optional[str] = None
    upDate: Optional[str] = None
    trDate: Optional[str] = None
