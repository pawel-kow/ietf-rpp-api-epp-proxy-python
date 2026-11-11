from dataclasses import dataclass

from dataclasses_json import Undefined, dataclass_json

from rpp.dto.rpp_object import RPPObject, type_field


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPDiscoveryEnvironment(RPPObject):
    at_type: str = type_field("discoveryEnvironment")
    name: str
    status: str
