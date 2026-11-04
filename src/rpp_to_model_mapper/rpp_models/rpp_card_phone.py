from dataclasses import dataclass
from typing import Dict, Optional

from dataclasses_json import Undefined, dataclass_json

from .rpp_object import RPPObject


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPCardPhone(RPPObject):
    number: str
    features: Optional[Dict[str, bool]] = None
