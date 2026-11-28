from dataclasses import dataclass, field
from typing import Optional

from dataclasses_json import dataclass_json, Undefined

from rpp.dto.rpp_object import RPPObject, type_field


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPVerificationInformation(RPPObject):
    """The Verification Information Object of the rri extension (docs/rri/rri-extension.md)."""
    at_type: str = type_field("verificationInformation")
    claims: list[str] = field(default_factory=list)
    result: str
    reference: Optional[str] = None
    date: Optional[str] = None
    evidence: Optional[str] = None
    method: Optional[str] = None
    trustFramework: Optional[str] = None
