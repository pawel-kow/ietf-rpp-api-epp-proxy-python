from core.model.contact.address import Address
from core.model.contact.contacts import Contact, ContactType
from core.model.contact.localized_postal_info import LocalizedPostalInfo
from rpp.schema.validator import validate_schema
from rpp.mapping.contact import phones
from rpp.mapping.shared import auth_info, prov_metadata, statuses
from rpp.mapping.shared.common import parse_rpp, reject_set
from core.capabilities.not_supported_by_backend import NotSupportedByBackend
from core.capabilities.not_supported_by_proxy import NotSupportedByProxy
from rpp.dto.rpp_card import RPPCard
from rpp.dto.rpp_card_address import RPPCardAddress
from rpp.dto.rpp_card_address_component import RPPCardAddressComponent
from rpp.dto.rpp_card_email import RPPCardEmail
from rpp.dto.rpp_card_localization import RPPCardLocalization
from rpp.dto.rpp_card_name import RPPCardName
from rpp.dto.rpp_card_organization import RPPCardOrganization
from rpp.dto.rpp_card_phone import RPPCardPhone
from rpp.dto.rpp_contact import RPPContact

KIND_INDIVIDUAL = "individual"
KIND_ORG = "org"
KIND_TO_TYPE = {KIND_INDIVIDUAL: ContactType.PERSON, KIND_ORG: ContactType.ORG}
TYPE_TO_KIND = {contact_type: kind for kind, contact_type in KIND_TO_TYPE.items()}
COMPONENT_TO_ADDRESS = {"locality": "city", "region": "stateProvince", "postcode": "postalCode"}
MAX_STREET_LINES = 3  # RFC 5733
PHONE_VOICE = "voice"
PHONE_FAX = "fax"
# EPP keeps no language with its localized form. BCP 47: undetermined.
LANGUAGE_UNDETERMINED = "und"


def _check_key_sequence(entries: dict | None, base: str):
    """Numbered keys need the predefined key and may not leave gaps (profile §4.1.10)."""
    numbers = sorted(int(key.removeprefix(f"{base}-")) for key in entries or {} if key.startswith(f"{base}-"))
    if numbers and (base not in entries or numbers != list(range(1, len(numbers) + 1))):
        raise ValueError(f"Keys '{base}-N' need the key '{base}' and must be sequential")


def _check_ascii(card: RPPCard):
    """The internationalized form is US-ASCII (profile §4.1.11)."""
    values = [card.name.full] if card.name else []
    values += [organization.name for organization in (card.organizations or {}).values()]
    values += [c.value for address in (card.addresses or {}).values() for c in address.components]
    values += [email.address for email in (card.emails or {}).values()]
    if not all(value.isascii() for value in values):
        raise ValueError("The internationalized form must contain only US-ASCII characters")


def _check_phone_kinds(card: RPPCard):
    """The key and the features say the same (spec-issues.md)."""
    for key, phone in (card.phones or {}).items():
        features = set(phone.features or {})
        if features == {PHONE_VOICE, PHONE_FAX}:
            continue
        is_fax_key = key.split("-")[0] == PHONE_FAX
        if is_fax_key != (PHONE_FAX in features):
            raise ValueError(f"The features of phone '{key}' do not match its key")


def _check_profile(card: RPPCard):
    """What the JSContact profile requires and the schema cannot express."""
    _check_key_sequence(card.emails, "email")
    _check_key_sequence(card.phones, PHONE_VOICE)
    _check_key_sequence(card.phones, PHONE_FAX)
    _check_ascii(card)
    _check_phone_kinds(card)


def _reject_additional(entries: dict | None, member: str):
    """EPP holds only the entry under the predefined key."""
    if any("-" in key for key in entries or {}):
        raise NotSupportedByBackend(f"Additional entries in '{member}'")


def _rpp_to_type(card: RPPCard) -> ContactType:
    kind = card.kind or KIND_INDIVIDUAL
    if kind == KIND_INDIVIDUAL and card.organizations:
        raise NotSupportedByBackend("'organizations' on an individual")
    return KIND_TO_TYPE[kind]


def _rpp_to_address(addresses: dict[str, RPPCardAddress] | None) -> Address | None:
    if not addresses:
        return None
    rpp_address = addresses["addr"]
    address = Address(street=[], country=rpp_address.countryCode)
    for component in rpp_address.components:
        if component.kind == "name":
            address.street.append(component.value)
        else:
            setattr(address, COMPONENT_TO_ADDRESS[component.kind], component.value)
    if len(address.street) > MAX_STREET_LINES:
        raise NotSupportedByBackend(f"More than {MAX_STREET_LINES} street lines")
    address.street = address.street or None
    return address


def _rpp_to_phone(card: RPPCard, key: str) -> list[str] | None:
    phone = (card.phones or {}).get(key)
    return [phones.rpp_to_model(phone.number)] if phone else None


def _reject_multiple_features(card: RPPCard):
    for key, phone in (card.phones or {}).items():
        if set(phone.features or {}) == {PHONE_VOICE, PHONE_FAX}:
            raise NotSupportedByBackend(f"Phone '{key}' with both 'voice' and 'fax'")


def _organisation_name(organizations: dict | None) -> str | None:
    return organizations["org"].name if organizations else None


def _rpp_to_localized(card: RPPCard) -> LocalizedPostalInfo | None:
    """The localized form. EPP needs it complete, so what it leaves out comes from the Card."""
    localizations = card.localizations or {}
    if len(localizations) > 1:
        raise NotSupportedByBackend("More than one localization")
    localization = next(iter(localizations.values()), RPPCardLocalization())
    if localization == RPPCardLocalization():
        return None
    if localization.emails:
        raise NotSupportedByBackend("A localized email")
    if localization.organizations and (card.kind or KIND_INDIVIDUAL) == KIND_INDIVIDUAL:
        raise NotSupportedByBackend("'organizations' on an individual")
    name = localization.name or card.name
    return LocalizedPostalInfo(
        name=name.full if name else None,
        organisationName=_organisation_name(localization.organizations or card.organizations),
        address=_rpp_to_address(localization.addresses or card.addresses),
    )


def contact_from_rpp(contact_rpp: RPPContact) -> Contact:
    """The Contact a create, a full update or a patched contact asks for. Its status and `authInfo` are the caller's."""
    card = contact_rpp.contactInfo
    _check_profile(card)
    reject_set(links=card.links)
    if contact_rpp.disclose:
        raise NotSupportedByProxy("'disclose'")
    _reject_additional(card.emails, "emails")
    _reject_additional(card.phones, "phones")
    _reject_multiple_features(card)
    email = (card.emails or {}).get("email")
    return Contact(
        id=contact_rpp.id,
        type=_rpp_to_type(card),
        name=card.name.full if card.name else None,
        organisationName=_organisation_name(card.organizations),
        email=[email.address] if email else None,
        phone=_rpp_to_phone(card, PHONE_VOICE),
        fax=_rpp_to_phone(card, PHONE_FAX),
        address=_rpp_to_address(card.addresses),
        localizedPostalInfo=_rpp_to_localized(card),
    )


def rpp_to_model(rpp: dict) -> Contact:
    """Converts a create request to a Contact."""
    validate_schema("contact.create", rpp)
    contact_rpp = parse_rpp(RPPContact, rpp)
    contact = contact_from_rpp(contact_rpp)
    reject_set(status=contact_rpp.status)
    contact.authInfo = auth_info.rpp_to_model(contact_rpp.authInfo)
    return contact


def _address_to_rpp(address: Address | None) -> dict[str, RPPCardAddress] | None:
    if address is None:
        return None
    components = [RPPCardAddressComponent(kind="name", value=line) for line in address.street or []]
    components += [
        RPPCardAddressComponent(kind=kind, value=getattr(address, member))
        for kind, member in COMPONENT_TO_ADDRESS.items()
        if getattr(address, member)
    ]
    return {"addr": RPPCardAddress(components=components, countryCode=address.country)}


def _phones_to_rpp(contact: Contact) -> dict[str, RPPCardPhone] | None:
    numbers = {}
    if contact.phone and contact.phone[0]:
        numbers["voice"] = RPPCardPhone(number=phones.model_to_rpp(contact.phone[0]))
    if contact.fax and contact.fax[0]:
        numbers["fax"] = RPPCardPhone(number=phones.model_to_rpp(contact.fax[0]), features={"fax": True})
    return numbers or None


def _name_to_rpp(name: str | None) -> RPPCardName | None:
    return RPPCardName(full=name) if name else None


def _organizations_to_rpp(name: str | None) -> dict[str, RPPCardOrganization] | None:
    return {"org": RPPCardOrganization(name=name)} if name else None


def _localizations_to_rpp(contact: Contact) -> dict[str, RPPCardLocalization] | None:
    """The localized form, with the members that differ from the internationalized form."""
    localized = contact.localizedPostalInfo
    if localized is None:
        return None
    members = {}
    if localized.name != contact.name:
        members["name"] = _name_to_rpp(localized.name)
    if localized.organisationName != contact.organisationName:
        members["organizations"] = _organizations_to_rpp(localized.organisationName)
    if localized.address != contact.address:
        members["addresses"] = _address_to_rpp(localized.address)
    return {LANGUAGE_UNDETERMINED: RPPCardLocalization(**members)} if any(members.values()) else None


def _card_to_rpp(contact: Contact) -> RPPCard:
    email = contact.email[0] if contact.email else None
    return RPPCard(
        kind=TYPE_TO_KIND.get(contact.type),
        name=_name_to_rpp(contact.name),
        organizations=_organizations_to_rpp(contact.organisationName),
        addresses=_address_to_rpp(contact.address),
        phones=_phones_to_rpp(contact),
        emails={"email": RPPCardEmail(address=email)} if email else None,
        localizations=_localizations_to_rpp(contact),
    )


def model_to_rpp(contact: Contact) -> dict:
    """Converts a Contact to its read representation."""
    contact_dict = RPPContact(
        id=contact.id,
        provMetadata=prov_metadata.model_to_rpp(contact),
        status=statuses.model_to_rpp(contact, "contactStatus"),
        contactInfo=_card_to_rpp(contact),
        authInfo=auth_info.model_to_rpp(contact.authInfo),
    ).to_rpp()
    validate_schema("contact.read", contact_dict)
    return contact_dict
