from dataclasses import dataclass
from typing import Any, Dict, Optional

from dataclasses_json import dataclass_json, Undefined

from rpp.dto.rpp_object import RPPObject


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPPatchOperation(RPPObject):
    op: str
    path: str
    value: Optional[Any] = None
    match: Optional[Dict[str, Any]] = None
