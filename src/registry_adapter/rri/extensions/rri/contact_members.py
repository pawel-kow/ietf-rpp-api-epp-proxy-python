"""The verification information of a contact in RRI (docs/rri/rri-extension.md, "Mapping to DENIC RRI"): the
`verification:verificationInformation` blocks of contact INFO, CREATE and UPDATE."""
import logging
from datetime import datetime, timedelta, timezone

from xsdata.models.datatype import XmlDateTime

from extensions.rri.core.model.contact_verifications import ContactVerifications
from extensions.rri.core.model.verification_information import VerificationInformation
from registry_adapter.rri.commands.shared.rri_time import utc_time, utc_time_of_text
from registry_adapter.rri.xml.generated import verification_5_0 as rri

logger = logging.getLogger(__name__)

FIELD = "verification_information"


def _timestamp(block) -> str | None:
    """The date of a record in UTC. A value the proxy cannot read is left out, logged by the name of its field."""
    stated = getattr(block, "verification_timestamp", None)
    if stated is None:
        return None
    try:
        return utc_time(stated) if isinstance(stated, XmlDateTime) else utc_time_of_text(stated)
    except (ValueError, OverflowError, TypeError):
        logger.warning("A verificationTimestamp is no date and time the proxy can read")
        return None


def record_of(block) -> VerificationInformation:
    """A record of a block of an INFO, whichever type the registry states it as: the claims in lower case, the other values as
    stated. Raises AttributeError or TypeError for a block without claims or result."""
    block = getattr(block, "value", block)     # xsdata wraps a block stated with an `xsi:type` in a `DerivedElement`
    result = block.verification_result
    return VerificationInformation(
        claims=[str(claim).lower() for claim in block.verified_claims.claim],
        result=str(getattr(result, "value", result)),
        reference=getattr(block, "verification_reference", None),
        date=_timestamp(block),
        evidence=getattr(block, "verification_evidence", None),
        method=getattr(block, "verification_method", None),
        trust_framework=getattr(block, "trust_framework", None),
    )


def records_of(blocks) -> list[VerificationInformation]:
    """The records of the blocks of an INFO. A block the proxy cannot read is left out, logged without its values."""
    records = []
    for block in blocks:
        try:
            records.append(record_of(block))
        except (AttributeError, TypeError):
            logger.warning("A verification block of the registry cannot be read and is left out")
    return records


# MTEST refuses the date of a block in the form with `Z` (63200041861, checked 2026-11-28) and takes one with an offset,
# so a request states the instant at this offset (an instant is the same at any).
OFFSET = timezone(timedelta(hours=1))


def _instant(text: str) -> XmlDateTime:
    """The date of a request as the registry takes it: the instant at a fixed offset (`+01:00`), never `Z`. A date
    without an offset is taken as UTC."""
    moment = datetime.fromisoformat(text)
    moment = moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment
    moment = moment.astimezone(OFFSET)
    fraction = f".{moment.microsecond:06d}" if moment.microsecond else ""
    return XmlDateTime.from_string(f"{moment:%Y-%m-%dT%H:%M:%S}{fraction}+01:00")


def block_of(record: VerificationInformation) -> rri.VerificationInformationType:
    """The block of a request: every element is required. Raises ValueError for a record that lacks one or whose date is no
    date and time, which a request the schema validated does not."""
    values = (record.reference, record.date, record.evidence, record.method, record.trust_framework)
    if not record.claims or any(value is None for value in values):
        raise ValueError("A verification record of a request states every element")
    return rri.VerificationInformationType(
        verified_claims=rri.VerifiedClaimsType(claim=[claim.lower() for claim in record.claims]),
        verification_result=rri.VerificationResultType(record.result),
        verification_reference=record.reference,
        verification_timestamp=_instant(record.date),
        verification_evidence=record.evidence,
        verification_method=record.method,
        trust_framework=record.trust_framework,
    )


class ContactMembers:
    """What the rri extension adds to the contact commands (`RriExtensionPart.contact_members`)."""

    def read(self, data) -> ContactVerifications:
        """The records of a contact INFO."""
        return ContactVerifications(blocks=records_of(data.verification_information))

    def fields(self, held: ContactVerifications) -> dict:
        """The fields of CREATE and UPDATE that state the records."""
        return {FIELD: [block_of(record) for record in held.blocks]}


CONTACT_MEMBERS = ContactMembers()
