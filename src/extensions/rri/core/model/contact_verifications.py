from dataclasses import dataclass, field

from extensions.rri.core.model.verification_information import VerificationInformation


@dataclass(kw_only=True)
class ContactVerifications:
    """What the rri extension adds to a contact: its verification information, 0 to 5 records. In a replacement an empty list
    is the removal of the records the contact holds."""
    blocks: list[VerificationInformation] = field(default_factory=list)
