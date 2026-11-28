from dataclasses import dataclass
from typing import Optional

from dataclasses_json import dataclass_json, Undefined

from rpp.dto.rpp_object import RPPObject, type_field


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPReleaseProcess(RPPObject):
    """The Release Process Object of the rri extension (docs/rri/rri-extension.md)."""
    at_type: str = type_field("releaseProcess")
    keepNameservers: Optional[bool] = None
