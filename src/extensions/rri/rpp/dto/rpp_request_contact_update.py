from dataclasses import dataclass

from dataclasses_json import dataclass_json, Undefined

from rpp.dto.rpp_object import RPPObject, type_field


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPRequestContactUpdate(RPPObject):
    """A full update of a request contact: what a client may change of it."""
    at_type: str = type_field("requestContact")
    uriTemplate: str
