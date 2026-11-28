from dataclasses import dataclass
from typing import Optional

from dataclasses_json import dataclass_json, Undefined

from rpp.dto.rpp_contact_reference import RPPContactReference
from rpp.dto.rpp_object import RPPObject, type_field
from extensions.rri.rpp.dto.rpp_verification_information import RPPVerificationInformation


@dataclass_json(undefined=Undefined.RAISE)
@dataclass(kw_only=True)
class RPPHolderVerification(RPPObject):
    """The Holder Verification Object of the rri extension (docs/rri/rri-extension.md)."""
    at_type: str = type_field("holderVerification")
    holder: Optional[RPPContactReference] = None
    verifications: Optional[list[RPPVerificationInformation]] = None
