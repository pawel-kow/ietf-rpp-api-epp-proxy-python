from dataclasses import dataclass, field
from typing import Optional

from dataclasses_json import Undefined, config, dataclass_json

from .rpp_object import RPPObject


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPStatus(RPPObject):
    """A status object. Its '@type' depends on the object it belongs to."""
    at_type: str = field(metadata=config(field_name="@type"))
    label: str
    reason: Optional[str] = None
    due: Optional[str] = None
