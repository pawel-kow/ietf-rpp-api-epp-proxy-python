"""The Verification Information Object of the rri extension (docs/rri/rri-extension.md), model ↔ RPP, for a contact's
`verifications` and the holders of a verification process."""
import re
from datetime import datetime, timedelta, timezone

from extensions.rri.core.model.verification_information import VerificationInformation
from extensions.rri.rpp.dto.rpp_verification_information import RPPVerificationInformation
from extensions.rri.rpp.mapping.verification_date_refused import VerificationDateRefused
from rpp.mapping.shared.common import parse_rpp


# The offset the registry takes a date at, and which the adapter states it at (MTEST refuses `Z`, docs/rri/rri-extension.md).
OFFSET = timezone(timedelta(hours=1))

LOWER = re.compile("[tz]")


def instant(text: str) -> str:
    """The date of a record as RFC 3339 with `T` and `Z` in upper case (a lower case one is valid, and Python does not read it), checked to be an
    instant that can be stated at the offset of the registry. Raises `VerificationDateRefused`, with no part of the value in its message."""
    text = LOWER.sub(lambda match: match.group().upper(), text)
    try:
        moment = datetime.fromisoformat(text)
        (moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment).astimezone(OFFSET)
    except (ValueError, OverflowError):
        raise VerificationDateRefused("The date of a verification record is not an instant the server can state") from None
    return text


def rpp_to_model(rpp: dict) -> VerificationInformation:
    """A record of a request, whose schema the caller has validated."""
    record = parse_rpp(RPPVerificationInformation, rpp)
    return VerificationInformation(claims=list(record.claims), result=record.result, reference=record.reference,
                                   date=instant(record.date) if record.date is not None else None, evidence=record.evidence, method=record.method,
                                   trust_framework=record.trustFramework)


def model_to_dto(record: VerificationInformation) -> RPPVerificationInformation:
    return RPPVerificationInformation(claims=list(record.claims), result=record.result, reference=record.reference,
                                      date=record.date, evidence=record.evidence, method=record.method,
                                      trustFramework=record.trust_framework)
