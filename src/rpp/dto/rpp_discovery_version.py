from dataclasses import dataclass, field

from dataclasses_json import Undefined, config, dataclass_json

from rpp.dto.rpp_object import RPPObject, type_field


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPDiscoveryVersion(RPPObject):
    at_type: str = type_field("discoveryVersion")
    version: str
    base_url: str = field(metadata=config(field_name="baseUrl"))
