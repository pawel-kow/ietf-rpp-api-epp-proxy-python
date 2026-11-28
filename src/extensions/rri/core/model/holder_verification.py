from dataclasses import dataclass, field
from typing import Optional

from extensions.rri.core.model.verification_information import VerificationInformation


@dataclass(kw_only=True)
class HolderVerification:
    """The verification information of one holder of a domain name. `handle` is None where the registry does not show it."""
    handle: Optional[str] = None
    verifications: list[VerificationInformation] = field(default_factory=list)
