from dataclasses import dataclass

from dataclasses_json import dataclass_json, Undefined

from rpp.dto.rpp_object import RPPObject, type_field


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPExtension(RPPObject):
    """The Extension Object (json §6.2.12)."""
    at_type: str = type_field("extension")
    name: str
    id: str
    version: str
    url: str
