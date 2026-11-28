"""The Verification Information Object of the rri extension (docs/rri/rri-extension.md), model ↔ RPP, for a contact's
`verifications` and the holders of a verification process."""
from extensions.rri.core.model.verification_information import VerificationInformation
from extensions.rri.rpp.dto.rpp_verification_information import RPPVerificationInformation
from rpp.mapping.shared.common import parse_rpp


def rpp_to_model(rpp: dict) -> VerificationInformation:
    """A record of a request, whose schema the caller has validated."""
    record = parse_rpp(RPPVerificationInformation, rpp)
    return VerificationInformation(claims=list(record.claims), result=record.result, reference=record.reference,
                                   date=record.date, evidence=record.evidence, method=record.method,
                                   trust_framework=record.trustFramework)


def model_to_dto(record: VerificationInformation) -> RPPVerificationInformation:
    return RPPVerificationInformation(claims=list(record.claims), result=record.result, reference=record.reference,
                                      date=record.date, evidence=record.evidence, method=record.method,
                                      trustFramework=record.trust_framework)
