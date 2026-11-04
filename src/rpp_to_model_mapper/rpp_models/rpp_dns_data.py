from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dataclasses_json import Undefined, dataclass_json

from .rpp_dns_record import RPPDnsRecord
from .rpp_object import RPPObject, type_field


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPDnsData(RPPObject):
    at_type: str = type_field("dnsData")
    records: Optional[List[RPPDnsRecord]] = None
    controls: Optional[Dict[str, Any]] = None
