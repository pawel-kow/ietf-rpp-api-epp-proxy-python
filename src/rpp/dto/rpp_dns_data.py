from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dataclasses_json import dataclass_json, Undefined

from rpp.dto.rpp_dns_record import RPPDnsRecord
from rpp.dto.rpp_object import RPPObject, type_field


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPDnsData(RPPObject):
    at_type: str = type_field("dnsData")
    records: Optional[List[RPPDnsRecord]] = None
    controls: Optional[Dict[str, Any]] = None
