from dataclasses import dataclass, field, replace
from typing import Optional

from extensions.rri.core.model.holder_verification import HolderVerification
from extensions.rri.core.model.verification_information import VerificationInformation


@dataclass(kw_only=True)
class VerificationProcess:
    """The verification of the holders of a domain name that the registry requires, as a domain INFO shows it: the deadlines
    (UTC), the holders in their order, and the sponsor of the domain, which decides what a client may see. A domain without a
    deadline has no process."""
    sponsor_id: Optional[str] = None
    hold_deadline: Optional[str] = None
    deletion_deadline: Optional[str] = None
    holders: list[HolderVerification] = field(default_factory=list)

    @property
    def exists(self) -> bool:
        return bool(self.hold_deadline or self.deletion_deadline) and bool(self.holders)

    def reduced(self) -> "VerificationProcess":
        """What a client other than the sponsor may see: no holder handles, the claims and the result of each record only."""
        return replace(self, holders=[
            HolderVerification(verifications=[VerificationInformation(claims=list(record.claims), result=record.result)
                                              for record in holder.verifications])
            for holder in self.holders])
