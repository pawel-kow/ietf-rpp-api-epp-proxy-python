import logging

from jsonschema import ValidationError

from core.capabilities.backend_requirement import BackendRequirement
from core.model.contact.address import Address
from core.model.organisation.organisation import Organisation
from rpp.dto.rpp_card import RPPCard
from rpp.dto.rpp_card_address import RPPCardAddress
from rpp.dto.rpp_card_address_component import RPPCardAddressComponent
from rpp.dto.rpp_card_email import RPPCardEmail
from rpp.dto.rpp_card_name import RPPCardName
from rpp.dto.rpp_card_phone import RPPCardPhone
from rpp.dto.rpp_organisation import RPPOrganisation, RPPOrganisationReference, RPPOrganisationRole
from rpp.dto.rpp_prov_metadata import RPPProvMetadata
from rpp.dto.rpp_status import RPPStatus
from rpp.mapping.contact import phones
from rpp.mapping.contact.contacts import COMPONENT_TO_ADDRESS
from rpp.mapping.organisation.organisation_members import ORGANISATION_MEMBERS
from rpp.schema.validator import validate_schema

logger = logging.getLogger(__name__)

KIND_ORG = "org"


def _valid(definition: str, value: dict, member: str) -> bool:
    """Whether an optional entry of the Card fits its definition. One that does not is left out and its member named in the log
    (never its value): registry data the client cannot fix does not make the read fail."""
    try:
        validate_schema(definition, value)
        return True
    except ValidationError:
        logger.warning("An organisation read leaves out an entry of %s that fails its definition", member)
        return False


def _address(address: Address | None) -> dict | None:
    if address is None:
        return None
    components = [RPPCardAddressComponent(kind="name", value=line) for line in address.street or []]
    components += [RPPCardAddressComponent(kind=kind, value=getattr(address, member))
                   for kind, member in COMPONENT_TO_ADDRESS.items() if getattr(address, member)]
    rpp = RPPCardAddress(components=components, countryCode=address.country).to_rpp()
    return {"addr": rpp} if _valid("Address", rpp, "addresses") else None


def _numbers(numbers: list[str], base: str, features: dict | None) -> dict[str, dict]:
    entries = {}
    for number in numbers:
        try:
            entry = RPPCardPhone(number=phones.model_to_rpp(number), features=features).to_rpp()
        except BackendRequirement:
            logger.warning("An organisation read leaves out an entry of phones that is no number of the backend")
            continue
        if _valid("Phone", entry, "phones"):
            entries[base if not entries else f"{base}-{len(entries)}"] = entry
    return entries


def _links(urls: list[str]) -> dict[str, dict]:
    """The first URL as `url`. The Card of the drafts has no `url-1` (`RecordLink` allows `url` and `contact-uri` only), so further
    URLs are left out (spec-issues.md, "url-n")."""
    entries = {}
    for url in urls:
        entry = {"uri": url}
        if "url" in entries:
            logger.warning("An organisation read leaves out a further entry of links: the Card has one url")
        elif _valid("Link", entry, "links"):
            entries["url"] = entry
    return entries


def _card(organisation: Organisation) -> RPPCard:
    email = RPPCardEmail(address=organisation.email).to_rpp() if organisation.email else None
    phone_entries = {**_numbers(organisation.phones, "voice", None), **_numbers(organisation.faxes, "fax", {"fax": True})}
    return RPPCard(
        kind=KIND_ORG,
        name=RPPCardName(full=organisation.name) if organisation.name else None,
        addresses=_address(organisation.address),
        phones=phone_entries or None,
        emails={"email": email} if email and _valid("EmailAddress", email, "emails") else None,
        links=_links(organisation.urls) or None,
    )


def _statuses(labels: list[str], status_type: str) -> list[RPPStatus]:
    return [RPPStatus(at_type=status_type, label=label) for label in labels]


def model_to_rpp(organisation: Organisation, extensions: tuple[str, ...] = ()) -> dict:
    """Converts an Organisation to its read representation, with the members the offered `extensions` add."""
    rpp = RPPOrganisation(
        id=organisation.id,
        provMetadata=RPPProvMetadata(spClientId=organisation.sponsor_id, upDate=organisation.up_date),
        status=_statuses(organisation.status, "organisationStatus"),
        roles={role: RPPOrganisationRole(status=_statuses(labels, "organisationRoleStatus"))
               for role, labels in organisation.roles.items()},
        parent=RPPOrganisationReference(id=organisation.parent) if organisation.parent else None,
        contactInfo=_card(organisation),
    ).to_rpp()
    rpp.update(ORGANISATION_MEMBERS.to_rpp(organisation, "organisation.read", extensions))
    validate_schema("organisation.read", rpp, extensions=extensions)
    return rpp
