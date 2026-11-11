from typing import Union

from core.model.contact.contacts import Contact, ContactType
from core.model.contact.localized_postal_info import LocalizedPostalInfo
from core.model.shared.common import AuthInfo
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from registry_adapter.epp.commands.contact.common import address_of, phone_of
from registry_adapter.epp.commands.shared.epp_core import get_epp_error_response
from registry_adapter.epp.commands.shared.epp_response import (
    cl_trid, epp_datetime, find_res_data, parse_epp_response_header, status_reasons,
)
from registry_adapter.epp.session.epp_client import EPPClient
from registry_adapter.epp.xml.codec import epp_to_str, str_to_epp
from registry_adapter.epp.xml.generated.contact_1_0 import CreData, InfData, Info, PostalInfoEnumType
from registry_adapter.epp.xml.generated.epp_1_0 import CommandType, Epp, ReadWriteType


def contact_info(contact_id: str, rpp_cl_trid: str) -> Epp:
    return Epp(
        command=CommandType(
            info=ReadWriteType(other_element=Info(id=contact_id)),
            cl_trid=rpp_cl_trid,
        )
    )


def info_contact_xml(id: str, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(contact_info(id, cl_trid(client_request_id)), ns_map)


def parse_contact_response(xml_string: str, client_transaction_id: str) -> Union[OperationResponse[Contact], ErrorResponse]:
    """Parses an EPP contact create/info response: the payload is the contact."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None

    data = find_res_data(epp, InfData, CreData)

    postal_infos = {p.type_value: p for p in (getattr(data, "postal_info", None) or [])} if data else {}
    postal = postal_infos.get(PostalInfoEnumType.INT)
    localized_postal = postal_infos.get(PostalInfoEnumType.LOC)

    # The backend may send empty elements (<contact:org></contact:org>), which
    # xsdata parses as "" rather than None; treat empty as absent.
    name = (postal.name or None) if postal else None
    org = (postal.org or None) if postal else None
    address = address_of(postal)
    localized = None
    if localized_postal is not None:
        localized = LocalizedPostalInfo(
            name=localized_postal.name or None,
            organisationName=localized_postal.org or None,
            address=address_of(localized_postal),
        )

    email = [(getattr(data, "email", None) or None)] if data else [None]

    auth_info = getattr(data, "auth_info", None) if data else None
    pw = auth_info.pw.value if auth_info is not None and auth_info.pw is not None else None

    contact = Contact(
        id=data.id if data else None,
        roid=(getattr(data, "roid", None) or None) if data else None,
        name=name,
        organisationName=org,
        type=ContactType.ORG if org is not None or (localized and localized.organisationName)
            else ContactType.PERSON if name is not None or (localized and localized.name)
            else ContactType.UNDEFINED,
        email=email,
        phone=phone_of(getattr(data, "voice", None)) if data else None,
        fax=phone_of(getattr(data, "fax", None)) if data else None,
        address=address,
        localizedPostalInfo=localized,
        # common fields
        status=[s.s.value for s in getattr(data, "status", [])] if data else None,
        status_reasons=status_reasons(data) if data else {},
        crDate=epp_datetime(getattr(data, "cr_date", None)) if data else None,
        exDate=None,
        upDate=epp_datetime(getattr(data, "up_date", None)) if data else None,
        trDate=epp_datetime(getattr(data, "tr_date", None)) if data else None,
        clID=getattr(data, "cl_id", None) if data else None,
        crID=getattr(data, "cr_id", None) if data else None,
        upID=(getattr(data, "up_id", None) or None) if data else None,
        authInfo=AuthInfo(pw=pw, hash=None) if pw is not None else None,
    )

    return OperationResponse(payload=contact, **header)


def epp_contacts_Info(epp_client: EPPClient, id: str, client_transaction_id=None, *, ns_map: dict[str, str]) -> Union[OperationResponse[Contact], ErrorResponse]:
    """
    Retrieves information about a contact using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        id (str): The id of the contact to be retrieved.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        OperationResponse[Contact]: The response from the EPP server.
    """
    eppxml = info_contact_xml(id, client_request_id=client_transaction_id, ns_map=ns_map)
    success, code, response = epp_client.send_and_get_response(eppxml)
    
    if success == True:
        contactresp = parse_contact_response(response, client_transaction_id=client_transaction_id)
        return contactresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp
