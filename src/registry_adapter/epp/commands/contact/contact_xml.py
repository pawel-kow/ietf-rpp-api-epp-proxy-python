from models import *
from typing import Union
from registry_adapter.epp.commands.shared.epp_response import (
    cl_trid, epp_datetime, find_res_data, parse_epp_response_header, status_reasons,
)
from registry_adapter.epp.commands.contact.epp_request import (
    contact_check, contact_create, contact_delete, contact_info, contact_transfer, contact_update,
)
from registry_adapter.epp.xml.codec import epp_to_str, str_to_epp
from registry_adapter.epp.xml.generated.contact_1_0 import ChkData, CreData, InfData, PostalInfoEnumType, TrnData
from registry_adapter.epp.xml.generated.epp_1_0 import Epp


def _phone(e164):
    """Map an EPP e164Type back to the RPP phone string ('+1.703...x1234')."""
    if e164 is None or not e164.value:
        return None
    return [f"{e164.value}x{e164.x}" if e164.x else e164.value]


def _address(postal) -> Address | None:
    if postal is None or postal.addr is None:
        return None
    a = postal.addr
    return Address(
        street=[line for line in a.street if line] or None,
        city=a.city or None,
        stateProvince=a.sp or None,
        postalCode=a.pc or None,
        country=a.cc or None,
    )


def create_contact_xml(contact: Contact, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(contact_create(contact, cl_trid(client_request_id)), ns_map)


def contact_check_xml(id: str, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(contact_check(id, cl_trid(client_request_id)), ns_map)


def info_contact_xml(id: str, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(contact_info(id, cl_trid(client_request_id)), ns_map)


def delete_contact_xml(id: str, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(contact_delete(id, cl_trid(client_request_id)), ns_map)


def transfer_contact_xml(transfer: ContactTransfer, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(contact_transfer(transfer, cl_trid(client_request_id)), ns_map)


def parse_contact_transfer_response(xml_string: str, client_transaction_id: str | None) -> ContactTransferResponse:
    """Parses an EPP contact transfer response, which is the same for every operation."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    data = find_res_data(epp, TrnData)
    if data is None:  # applied, but EPP gave no state
        return ContactTransferResponse(transfer=None, **header)
    return ContactTransferResponse(
        transfer=ContactTransferProcess(
            id=data.id,
            trStatus=data.tr_status.value,
            reqClientId=data.re_id,
            requestDate=epp_datetime(data.re_date),
            actClientId=data.ac_id,
            actionDate=epp_datetime(data.ac_date),
        ),
        **header,
    )


def parse_contact_delete_response(xml_string: str, client_transaction_id: str) -> Union[ContactDeleteResponse, ErrorResponse]:
    """Parses an EPP contact delete response."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    return ContactDeleteResponse(**header)


def parse_contact_response(xml_string: str, client_transaction_id: str) -> Union[ContactCreateResponse, ErrorResponse]:
    """Parses an EPP contact create/info response into a ContactCreateResponse."""
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
    address = _address(postal)
    localized = None
    if localized_postal is not None:
        localized = LocalizedPostalInfo(
            name=localized_postal.name or None,
            organisationName=localized_postal.org or None,
            address=_address(localized_postal),
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
        phone=_phone(getattr(data, "voice", None)) if data else None,
        fax=_phone(getattr(data, "fax", None)) if data else None,
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

    return ContactCreateResponse(contact=contact, **header)


def update_contact_xml(update: ContactUpdate, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(contact_update(update, cl_trid(client_request_id)), ns_map)


def parse_contact_update_response(xml_string: str, client_transaction_id: str | None) -> ContactUpdateResponse:
    """Parses an EPP contact update response."""
    header = parse_epp_response_header(str_to_epp(xml_string))
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    return ContactUpdateResponse(**header)


def parse_contact_check_response(xml_string: str, contact_id: str, client_transaction_id: str | None) -> ContactCheckResponse:
    """Parses the answer to a single-id check. The backend can change the case of the id."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    result = find_res_data(epp, ChkData).cd[0]
    return ContactCheckResponse(
        contact_id=contact_id,
        available=result.id.avail,
        reason=result.reason.value if result.reason else None,
        **header,
    )
