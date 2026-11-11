from dataclasses import dataclass
from typing import Optional

from dataclasses_json import Undefined, dataclass_json

from .rpp_object import RPPObject, type_field


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPRestoreReport(RPPObject):
    at_type: str = type_field("restoreReport")
    preData: Optional[str] = None
    postData: Optional[str] = None
    deleteTime: Optional[str] = None
    restoreTime: Optional[str] = None
    restoreReason: Optional[str] = None
    statements: Optional[list[str]] = None
    other: Optional[str] = None
