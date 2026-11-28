from dataclasses import dataclass
from typing import Optional

from dataclasses_json import dataclass_json, Undefined

from rpp.dto.rpp_object import RPPObject, type_field
from extensions.rri.rpp.dto.rpp_holder_verification import RPPHolderVerification


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPVerificationProcess(RPPObject):
    """The Verification Process Object of the rri extension (docs/rri/rri-extension.md)."""
    at_type: str = type_field("verificationProcess")
    holdDeadline: Optional[str] = None
    deletionDeadline: Optional[str] = None
    holders: list[RPPHolderVerification]
