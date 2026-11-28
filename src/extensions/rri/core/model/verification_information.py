from dataclasses import dataclass, field
from typing import Optional


@dataclass(kw_only=True)
class VerificationInformation:
    """A record of a verification of the contact information of a contact (docs/rri/rri-extension.md). A request states
    every element; a read states what the registry returns, and the claims, evidence, method and trust framework as it
    states them. `date` is an RFC 3339 date and time (a read: UTC)."""
    claims: list[str] = field(default_factory=list)
    result: str
    reference: Optional[str] = None
    date: Optional[str] = None
    evidence: Optional[str] = None
    method: Optional[str] = None
    trust_framework: Optional[str] = None
