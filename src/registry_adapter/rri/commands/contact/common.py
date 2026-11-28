"""The contact model ↔ RRI XML. RRI holds one postal form, one phone, no fax, no region and no authInfo."""
from core.model.contact.address import Address
from core.model.contact.contacts import Contact, ContactType
from core.result.result_code import ResultCode
from registry_adapter.rri.commands.shared.rri_time import utc_time
from registry_adapter.rri.xml.generated import contact_5_0 as rri

# "At least one Contact does not exist" is the contact itself for a command on one contact.
CONTACT_CODES = {
    "53000060009": ResultCode.OBJECT_DOES_NOT_EXIST,
    # Verification information (docs/rri/rri-extension.md, refusals): a value the registry refuses is a syntax error of the
    # request, a combination it does not allow (or conflicting claims) a policy error.
    **{code: ResultCode.PARAMETER_VALUE_SYNTAX_ERROR for code in (
        "63200041860", "63200041861", "63200041862", "63200041864", "63200041865", "63200041866")},
    "63200041863": ResultCode.PARAMETER_VALUE_POLICY_ERROR,
    "63200041867": ResultCode.PARAMETER_VALUE_POLICY_ERROR,
}

PERSON = "PERSON"

ORG = "ORG"

REQUEST = "REQUEST"


def regacc_of(handle: str) -> str:
    """A handle starts with the RegAccId of the RegAcc that administers it (`DENIC-1000022-…`)."""
    return "-".join(handle.split("-")[:2]).upper()


def fields_of(contact_type: ContactType, name: str | None, organisation: str | None, address: Address | None,
              email: list[str] | None, phone: list[str] | None) -> dict:
    """The fields of CREATE and UPDATE. An ORG is named by its organisation and has no `organisation` of its own."""
    rri_type = ORG if contact_type == ContactType.ORG else PERSON
    rri_name = (organisation or name) if rri_type == ORG else name
    postal = None
    if address is not None:
        postal = rri.PostalType(
            address=[rri.AddressType(value=line) for line in address.street or []],
            postal_code=rri.PostalCodeType(value=address.postalCode) if address.postalCode else None,
            city=rri.CityType(value=address.city) if address.city else None,
            country_code=rri.CountryCodeType(value=address.country) if address.country else None,
        )
    return dict(
        type_value=rri.TypeType(value=rri_type),
        name=rri.NameType(value=rri_name) if rri_name else None,
        organisation=[rri.OrganisationType(value=organisation)] if organisation and rri_type == PERSON else [],
        postal=postal,
        email=[rri.EmailType(value=value) for value in email or []],
        phone=rri.PhoneType(value=phone[0]) if phone else None,
    )


def _text(value) -> str | None:
    return value.value if value is not None else None


def changed_of(data: rri.InfoData) -> str | None:
    """The `changed` of an INFO, in the UTC form the EPP adapter gives too."""
    if not data.changed:
        return None
    return utc_time(data.changed)


def contact_from_rri(data: rri.InfoData) -> Contact:
    """A contact from its INFO. RRI has no contact status, so it is `ok` (gap Q14). Its verification data is
    carried over, so a full update can send it again."""
    rri_type = _text(data.type_value)
    is_org = rri_type == ORG
    postal = data.postal
    address = None
    if postal is not None:
        address = Address(street=[line.value for line in postal.address] or None, city=_text(postal.city),
                          postalCode=_text(postal.postal_code), country=_text(postal.country_code))
    handle = data.handle.value
    return Contact(
        id=handle,
        type=ContactType.ORG if is_org else ContactType.PERSON,
        name=_text(data.name),
        organisationName=_text(data.name) if is_org else (data.organisation[0].value if data.organisation else None),
        email=[e.value for e in data.email] or None,
        phone=[data.phone.value] if data.phone else None,
        address=address,
        status=["ok"],
        clID=regacc_of(handle),
        upDate=changed_of(data),
        carried_over=list(data.verification_information),
    )
