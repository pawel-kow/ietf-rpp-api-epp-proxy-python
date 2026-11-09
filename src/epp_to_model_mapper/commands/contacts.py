import re

from models import Address, AuthInfo, Contact, ContactTransfer, ContactType

from ..epp_model.contact_1_0 import (
    AddrType,
    AuthInfoType,
    Check,
    Create,
    Delete,
    E164Type,
    Info,
    PostalInfoEnumType,
    PostalInfoType,
    Transfer,
)
from ..epp_model.epp_1_0 import CommandType, Epp, ReadWriteType, TransferOpType, TransferType
from ..epp_model.eppcom_1_0 import PwAuthInfoType


def _e164(value: str) -> E164Type:
    """Split an RPP phone string ('+1.7035555555x1234') into an EPP e164Type."""
    match = re.search(r"x(\d+)", value)
    if match:
        return E164Type(value=re.sub(r"x\d+", "", value).strip(), x=match.group(1))
    return E164Type(value=value)


def _postal_info(kind: PostalInfoEnumType, name: str | None, org: str | None, address: Address | None) -> PostalInfoType:
    postal = PostalInfoType(type_value=kind)
    if name:
        postal.name = name
    if org:
        postal.org = org
    if address:
        addr = AddrType()
        if address.street:
            addr.street = list(address.street)
        addr.city = address.city
        addr.sp = address.stateProvince
        addr.pc = address.postalCode
        addr.cc = address.country
        postal.addr = addr
    return postal


def contact_create(contact: Contact, rpp_cl_trid: str) -> Epp:
    create = Create()

    if contact.id:
        create.id = contact.id.upper()

    is_org = contact.organisationName and contact.type == ContactType.ORG
    if contact.name or contact.address or is_org:
        create.postal_info.append(_postal_info(
            PostalInfoEnumType.INT, contact.name, contact.organisationName if is_org else None, contact.address,
        ))
    localized = contact.localizedPostalInfo
    if localized:
        create.postal_info.append(_postal_info(
            PostalInfoEnumType.LOC, localized.name, localized.organisationName, localized.address,
        ))

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


def _transfer_auth_info(auth_info: AuthInfo) -> AuthInfoType:
    return AuthInfoType(pw=PwAuthInfoType(value=auth_info.pw, roid=auth_info.roid))


def contact_transfer(transfer: ContactTransfer, rpp_cl_trid: str) -> Epp:
    return Epp(
        command=CommandType(
            transfer=TransferType(
                op=TransferOpType(transfer.operation.value),
                other_element=Transfer(
                    id=transfer.id.upper(),
                    auth_info=_transfer_auth_info(transfer.authInfo) if transfer.authInfo else None,
                ),
            ),
            cl_trid=rpp_cl_trid,
        )
    )

def contact_check(contact_id: str, rpp_cl_trid: str) -> Epp:
    return Epp(command=CommandType(check=ReadWriteType(other_element=Check(id=[contact_id.upper()])), cl_trid=rpp_cl_trid))
