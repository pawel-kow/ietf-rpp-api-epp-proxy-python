from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from dataclasses_json import Undefined, config, dataclass_json

from .rpp_object import RPPObject, type_field


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPDnsRecord(RPPObject):
    at_type: str = type_field("dnsRecord")
    name: str
    type: str
    rdata: Dict[str, Any]
    record_class: Optional[str] = field(default=None, metadata=config(field_name="class"))
