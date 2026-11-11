from dataclasses import dataclass
from typing import List, Optional

from dataclasses_json import Undefined, dataclass_json

from rpp.dto.rpp_dns_data import RPPDnsData
from rpp.dto.rpp_object import RPPObject, type_field
from rpp.dto.rpp_prov_metadata import RPPProvMetadata
from rpp.dto.rpp_status import RPPStatus


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPHost(RPPObject):
    at_type: str = type_field("host")
    hostName: str
    provMetadata: Optional[RPPProvMetadata] = None
    status: Optional[List[RPPStatus]] = None
    dns: Optional[RPPDnsData] = None
