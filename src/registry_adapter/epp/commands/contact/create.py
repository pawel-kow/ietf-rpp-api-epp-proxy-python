from typing import Union

from core.model.contact.address import Address
from core.model.contact.contacts import Contact, ContactType
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from registry_adapter.epp.commands.contact.common import e164_of
from registry_adapter.epp.commands.contact.info import parse_contact_response
from registry_adapter.epp.commands.shared.epp_core import get_epp_error_response
from registry_adapter.epp.commands.shared.epp_response import cl_trid
from registry_adapter.epp.session.epp_client import EPPClient
from registry_adapter.epp.xml.codec import epp_to_str
from registry_adapter.epp.xml.generated.contact_1_0 import (
    AddrType, AuthInfoType, Create, PostalInfoEnumType, PostalInfoType,
)
from registry_adapter.epp.xml.generated.epp_1_0 import CommandType, Epp, ReadWriteType
from registry_adapter.epp.xml.generated.eppcom_1_0 import PwAuthInfoType


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
        create.voice = e164_of(contact.phone[0])

    if contact.fax and len(contact.fax) > 0:
        create.fax = e164_of(contact.fax[0])

    if contact.authInfo and contact.authInfo.pw:
        create.auth_info = AuthInfoType(pw=PwAuthInfoType(value=contact.authInfo.pw))

    return Epp(
        command=CommandType(
            create=ReadWriteType(other_element=create),
            cl_trid=rpp_cl_trid,
        )
    )


def create_contact_xml(contact: Contact, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(contact_create(contact, cl_trid(client_request_id)), ns_map)


def epp_contacts_Create(epp_client: EPPClient, contact: Contact, client_transaction_id=None, *, ns_map: dict[str, str]) -> Union[OperationResponse[Contact], ErrorResponse]:
    """
    Creates a contact using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        contact (Contact): The contact object to be created.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        OperationResponse[Contact]: The response from the EPP server.
    """
    eppxml = create_contact_xml(contact, client_request_id=client_transaction_id, ns_map=ns_map)
    success, code, response = epp_client.send_and_get_response(eppxml)

    if success == True:
        contactresp = parse_contact_response(response, client_transaction_id=client_transaction_id)
        return contactresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp
