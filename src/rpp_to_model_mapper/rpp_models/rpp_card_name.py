from dataclasses import dataclass
from typing import Dict, List, Optional

from dataclasses_json import Undefined, dataclass_json

from .rpp_object import RPPObject


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPCardName(RPPObject):
    full: Optional[str] = None
    components: Optional[List[Dict[str, str]]] = None
