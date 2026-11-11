from dataclasses import dataclass, field
from typing import Optional

__NAMESPACE__ = "urn:ietf:params:xml:ns:idn-1.0"


@dataclass
class IdnDataType:
    class Meta:
        name = "idnDataType"

    table: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:idn-1.0",
            "required": True,
            "min_length": 1,
        },
    )
    uname: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "namespace": "urn:ietf:params:xml:ns:idn-1.0",
            "min_length": 1,
            "max_length": 255,
        },
    )


@dataclass
class Data(IdnDataType):
    class Meta:
        name = "data"
        namespace = "urn:ietf:params:xml:ns:idn-1.0"
