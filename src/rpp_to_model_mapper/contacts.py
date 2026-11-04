from models import Address, Contact, ContactType
from rpp_schema_validator import validate_schema
from .common import (
    auth_info_to_rpp, parse_rpp, prov_metadata_to_rpp, reject_set, rpp_to_auth_info, statuses_to_rpp,
)
from .phones import epp_to_tel, tel_to_epp
from .rpp_models import (
    RPPCard, RPPCardAddress, RPPCardAddressComponent, RPPCardEmail, RPPCardName,
    RPPCardOrganization, RPPCardPhone, RPPContact,
)
from .unsupported_rpp_feature import UnsupportedRppFeature

KIND_INDIVIDUAL = "individual"
KIND_ORG = "org"
KIND_TO_TYPE = {KIND_INDIVIDUAL: ContactType.PERSON, KIND_ORG: ContactType.ORG}
TYPE_TO_KIND = {contact_type: kind for kind, contact_type in KIND_TO_TYPE.items()}
COMPONENT_TO_ADDRESS = {"locality": "city", "region": "stateProvince", "postcode": "postalCode"}


def _single(entries: dict | None, member: str):
    """EPP holds one value where a Card holds a map."""
    if not entries:
        return None
    if len(entries) > 1:
        raise UnsupportedRppFeature(f"More than one entry in '{member}' is not supported")
    return next(iter(entries.values()))


def _rpp_to_type(card: RPPCard) -> ContactType:
    kind = card.kind or KIND_INDIVIDUAL
    if kind == KIND_INDIVIDUAL and card.organizations:
        raise UnsupportedRppFeature("'organizations' on an individual is not supported")
    return KIND_TO_TYPE[kind]


def _rpp_to_name(card: RPPCard) -> str | None:
    if card.name is None:
        return None
    if card.name.components and not card.name.full:
        raise UnsupportedRppFeature("'name.components' without 'name.full' is not supported")
    return card.name.full


def _rpp_to_address(card: RPPCard) -> Address | None:
    rpp_address = _single(card.addresses, "addresses")
    if rpp_address is None:
        return None
    if rpp_address.full and not rpp_address.components:
        raise UnsupportedRppFeature("An address with only 'full' is not supported")
    address = Address(street=[], country=rpp_address.countryCode)
    for component in rpp_address.components or []:
        if component.kind == "name":
            address.street.append(component.value)
        elif component.kind in COMPONENT_TO_ADDRESS:
            setattr(address, COMPONENT_TO_ADDRESS[component.kind], component.value)
        else:
            raise UnsupportedRppFeature(f"Address component '{component.kind}' is not supported")
    address.street = address.street or None
    return address


def _is_fax(phone: RPPCardPhone) -> bool:
    features = {name for name, enabled in (phone.features or {}).items() if enabled}
    if not features <= {"voice"} and features != {"fax"}:
        raise UnsupportedRppFeature(f"Phone features {sorted(features)} are not supported")
    return features == {"fax"}


def _rpp_to_phones(card: RPPCard) -> tuple[list[str] | None, list[str] | None]:
    phones = list((card.phones or {}).values())
    voice = {str(i): p for i, p in enumerate(phones) if not _is_fax(p)}
    fax = {str(i): p for i, p in enumerate(phones) if _is_fax(p)}
    return tuple(
        [tel_to_epp(phone.number)] if phone else None
        for phone in (_single(voice, "phones"), _single(fax, "phones"))
    )


def rpp_to_contact(rpp: dict) -> Contact:
    """Converts a create request to a Contact."""
    validate_schema("contact.create", rpp)
    contact_rpp = parse_rpp(RPPContact, rpp)
    card = contact_rpp.contactInfo
    reject_set(
        status=contact_rpp.status, disclose=contact_rpp.disclose, language=card.language,
        links=card.links, localizations=card.localizations,
    )
    organization = _single(card.organizations, "organizations")
    email = _single(card.emails, "emails")
    phone, fax = _rpp_to_phones(card)
    return Contact(
        id=contact_rpp.id,
        type=_rpp_to_type(card),
        name=_rpp_to_name(card),
        organisationName=organization.name if organization else None,
        email=[email.address] if email else None,
        phone=phone,
        fax=fax,
        address=_rpp_to_address(card),
        authInfo=rpp_to_auth_info(contact_rpp.authInfo),
    )


def _address_to_rpp(address: Address | None) -> dict[str, RPPCardAddress] | None:
    if address is None:
        return None
    components = [RPPCardAddressComponent(kind="name", value=line) for line in address.street or []]
    components += [
        RPPCardAddressComponent(kind=kind, value=getattr(address, member))
        for kind, member in COMPONENT_TO_ADDRESS.items()
        if getattr(address, member)
    ]
    return {"addr": RPPCardAddress(components=components or None, countryCode=address.country or None)}


def _phones_to_rpp(contact: Contact) -> dict[str, RPPCardPhone] | None:
    phones = {}
    if contact.phone and contact.phone[0]:
        phones["voice"] = RPPCardPhone(number=epp_to_tel(contact.phone[0]))
    if contact.fax and contact.fax[0]:
        phones["fax"] = RPPCardPhone(number=epp_to_tel(contact.fax[0]), features={"fax": True})
    return phones or None


def _card_to_rpp(contact: Contact) -> RPPCard:
    email = contact.email[0] if contact.email else None
    return RPPCard(
        kind=TYPE_TO_KIND.get(contact.type),
        name=RPPCardName(full=contact.name) if contact.name else None,
        organizations={"org": RPPCardOrganization(name=contact.organisationName)}
        if contact.organisationName else None,
        addresses=_address_to_rpp(contact.address),
        phones=_phones_to_rpp(contact),
        emails={"email": RPPCardEmail(address=email)} if email else None,
    )


def contact_to_rpp(contact: Contact) -> dict:
    """Converts a Contact to its read representation."""
    contact_dict = RPPContact(
        id=contact.id,
        provMetadata=prov_metadata_to_rpp(contact),
        status=statuses_to_rpp(contact, "contactStatus"),
        contactInfo=_card_to_rpp(contact),
        authInfo=auth_info_to_rpp(contact.authInfo),
    ).to_rpp()
    validate_schema("contact.read", contact_dict)
    return contact_dict
