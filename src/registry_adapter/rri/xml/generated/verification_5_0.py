from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from xsdata.models.datatype import XmlDateTime

__NAMESPACE__ = "http://registry.denic.de/verification/5.0"


class VerificationResultType(Enum):
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class VerifiedClaimsType:
    class Meta:
        name = "verifiedClaimsType"

    claim: list[str] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "namespace": "http://registry.denic.de/verification/5.0",
            "min_occurs": 1,
        },
    )


@dataclass
class VerificationInfoBaseType:
    class Meta:
        name = "verificationInfoBaseType"

    verified_claims: Optional[VerifiedClaimsType] = field(
        default=None,
        metadata={
            "name": "verifiedClaims",
            "type": "Element",
            "namespace": "http://registry.denic.de/verification/5.0",
            "required": True,
        },
    )
    verification_result: Optional[VerificationResultType] = field(
        default=None,
        metadata={
            "name": "verificationResult",
            "type": "Element",
            "namespace": "http://registry.denic.de/verification/5.0",
            "required": True,
        },
    )


@dataclass
class DomainVerificationInformationType(VerificationInfoBaseType):
    class Meta:
        name = "domainVerificationInformationType"

    verification_reference: Optional[str] = field(
        default=None,
        metadata={
            "name": "verificationReference",
            "type": "Element",
            "namespace": "http://registry.denic.de/verification/5.0",
        },
    )
    verification_timestamp: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "name": "verificationTimestamp",
            "type": "Element",
            "namespace": "http://registry.denic.de/verification/5.0",
        },
    )
    verification_evidence: Optional[str] = field(
        default=None,
        metadata={
            "name": "verificationEvidence",
            "type": "Element",
            "namespace": "http://registry.denic.de/verification/5.0",
        },
    )
    verification_method: Optional[str] = field(
        default=None,
        metadata={
            "name": "verificationMethod",
            "type": "Element",
            "namespace": "http://registry.denic.de/verification/5.0",
        },
    )
    trust_framework: Optional[str] = field(
        default=None,
        metadata={
            "name": "trustFramework",
            "type": "Element",
            "namespace": "http://registry.denic.de/verification/5.0",
        },
    )


@dataclass
class VerificationInformation(VerificationInfoBaseType):
    class Meta:
        name = "verificationInformation"
        namespace = "http://registry.denic.de/verification/5.0"


@dataclass
class VerificationInformationType(VerificationInfoBaseType):
    class Meta:
        name = "verificationInformationType"

    verification_reference: Optional[str] = field(
        default=None,
        metadata={
            "name": "verificationReference",
            "type": "Element",
            "namespace": "http://registry.denic.de/verification/5.0",
            "required": True,
        },
    )
    verification_timestamp: Optional[XmlDateTime] = field(
        default=None,
        metadata={
            "name": "verificationTimestamp",
            "type": "Element",
            "namespace": "http://registry.denic.de/verification/5.0",
            "required": True,
        },
    )
    verification_evidence: Optional[str] = field(
        default=None,
        metadata={
            "name": "verificationEvidence",
            "type": "Element",
            "namespace": "http://registry.denic.de/verification/5.0",
            "required": True,
        },
    )
    verification_method: Optional[str] = field(
        default=None,
        metadata={
            "name": "verificationMethod",
            "type": "Element",
            "namespace": "http://registry.denic.de/verification/5.0",
            "required": True,
        },
    )
    trust_framework: Optional[str] = field(
        default=None,
        metadata={
            "name": "trustFramework",
            "type": "Element",
            "namespace": "http://registry.denic.de/verification/5.0",
            "required": True,
        },
    )
