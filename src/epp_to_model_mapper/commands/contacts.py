import re

from models import Contact, ContactType

from ..epp_model.contact_1_0 import (
    AddrType,
    AuthInfoType,
    Create,
    Delete,
    E164Type,
    Info,
    PostalInfoEnumType,
    PostalInfoType,
)
from ..epp_model.epp_1_0 import CommandType, Epp, ReadWriteType
from ..epp_model.eppcom_1_0 import PwAuthInfoType


def _e164(value: str) -> E164Type:
    """Split an RPP phone string ('+1.7035555555x1234') into an EPP e164Type."""
    match = re.search(r"x(\d+)", value)
    if match:
        return E164Type(value=re.sub(r"x\d+", "", value).strip(), x=match.group(1))
    return E164Type(value=value)


def contact_create(contact: Contact, rpp_cl_trid: str) -> Epp:
    create = Create()

    if contact.id:
        create.id = contact.id.upper()

    is_org = contact.organisationName and contact.type == ContactType.ORG
    if contact.name or contact.address or is_org:
        postal = PostalInfoType(type_value=PostalInfoEnumType.INT)
        if contact.name:
            postal.name = contact.name
        if is_org:
            postal.org = contact.organisationName
        if contact.address:
            addr = AddrType()
            if contact.address.street:
                addr.street = list(contact.address.street)
            addr.city = contact.address.city
            addr.sp = contact.address.stateProvince
            addr.pc = contact.address.postalCode
            addr.cc = contact.address.country
            postal.addr = addr
        create.postal_info.append(postal)

    if contact.email and len(contact.email) > 0:
        create.email = contact.email[0]

    if contact.phone and len(contact.phone) > 0:
        create.voice = _e164(contact.phone[0])

    if contact.fax and len(contact.fax) > 0:
        create.fax = _e164(contact.fax[0])

    if contact.authInfo and contact.authInfo.pw:
        create.auth_info = AuthInfoType(pw=PwAuthInfoType(value=contact.authInfo.pw))

    return Epp(
        command=CommandType(
            create=ReadWriteType(other_element=create),
            cl_trid=rpp_cl_trid,
        )
    )


def contact_info(contact_id: str, rpp_cl_trid: str) -> Epp:
    return Epp(
        command=CommandType(
            info=ReadWriteType(other_element=Info(id=contact_id)),
            cl_trid=rpp_cl_trid,
        )
    )


def contact_delete(contact_id: str, rpp_cl_trid: str) -> Epp:
    return Epp(
        command=CommandType(
            delete=ReadWriteType(other_element=Delete(id=contact_id)),
            cl_trid=rpp_cl_trid,
        )
    )
