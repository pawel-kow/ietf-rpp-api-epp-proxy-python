from dataclasses import dataclass

from dataclasses_json import Undefined, dataclass_json

from .rpp_discovery_environment import RPPDiscoveryEnvironment
from .rpp_discovery_version import RPPDiscoveryVersion
from .rpp_object import RPPObject, type_field


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPDiscovery(RPPObject):
    at_type: str = type_field("discovery")
    versions: list[RPPDiscoveryVersion]
    environment: RPPDiscoveryEnvironment
    tlds: list[str]
    objects: list[str]
    datetime: str
