from dataclasses import dataclass
from typing import Optional

from dataclasses_json import Undefined, dataclass_json

from .rpp_object import RPPObject, type_field
from .rpp_restore_report import RPPRestoreReport


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPRestoreProcess(RPPObject):
    at_type: str = type_field("restoreProcess")
    restoreStatus: Optional[str] = None
    restoreReport: Optional[RPPRestoreReport] = None
