import uuid
from datetime import timezone
from models import *
from typing import Union
from .epp_core import map_epp_code
from .commands.contacts import contact_create, contact_delete, contact_info
from .commands.helper import epp_to_str, str_to_epp
from .epp_model.contact_1_0 import CreData, InfData
from .epp_model.epp_1_0 import Epp


def _parse_epp_response_header(epp: Epp) -> dict:
    return {
        "code": map_epp_code(epp.response.result[0].code.value),
        "msg": epp.response.result[0].msg.value,
        "server_transaction_id": epp.response.tr_id.sv_trid,
        "client_transaction_id": epp.response.tr_id.cl_trid,
    }


def _find_res_data(epp: Epp, *types):
    """Return the first res_data element matching one of the given xsdata types."""
    if epp.response is None or epp.response.res_data is None:
        return None
    for item in epp.response.res_data.other_element:
        if isinstance(item, types):
            return item
    return None


def _cl_trid(client_request_id) -> str:
    return client_request_id if client_request_id else str(uuid.uuid4())


def _dt(value):
    # UTC ISO form with fractional seconds and a trailing "Z", matching the EPP wire format.
    if value is None:
        return None
    return value.to_datetime().astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _phone(e164):
    """Map an EPP e164Type back to the RPP phone string ('+1.703...x1234')."""
    if e164 is None or not e164.value:
        return None
    return [f"{e164.value}x{e164.x}" if e164.x else e164.value]


def create_contact_xml(contact: Contact, client_request_id=None) -> str:
    return epp_to_str(contact_create(contact, _cl_trid(client_request_id)))


def info_contact_xml(id: str, client_request_id=None) -> str:
    return epp_to_str(contact_info(id, _cl_trid(client_request_id)))


def delete_contact_xml(id: str, client_request_id=None) -> str:
    return epp_to_str(contact_delete(id, _cl_trid(client_request_id)))


def parse_contact_delete_response(xml_string: str, client_transaction_id: str) -> Union[DomainDeleteResponse, ErrorResponse]:
    """Parses an EPP contact delete response.

    Returns a DomainDeleteResponse for compatibility with controller.contacts,
    which type-checks against DomainDeleteResponse (both are empty
    OperationResponse subclasses).
    """
    epp = str_to_epp(xml_string)
    header = _parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    return DomainDeleteResponse(**header)


def parse_contact_response(xml_string: str, client_transaction_id: str) -> Union[ContactCreateResponse, ErrorResponse]:
    """Parses an EPP contact create/info response into a ContactCreateResponse."""
    epp = str_to_epp(xml_string)
    header = _parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None

    data = _find_res_data(epp, InfData, CreData)

    postal = None
    postal_list = getattr(data, "postal_info", None) if data else None
    if postal_list:
        postal = postal_list[0]

    # The backend may send empty elements (<contact:org></contact:org>), which
    # xsdata parses as "" rather than None; treat empty as absent.
    name = (postal.name or None) if postal else None
    org = (postal.org or None) if postal else None
    address = None
    if postal is not None and postal.addr is not None:
        a = postal.addr
        address = Address(
            street=list(a.street) if a.street else None,
            city=a.city,
            stateProvince=a.sp,
            postalCode=a.pc,
            country=a.cc,
        )

    email = [(getattr(data, "email", None) or None)] if data else [None]

    auth_info = getattr(data, "auth_info", None) if data else None
    pw = auth_info.pw.value if auth_info is not None and auth_info.pw is not None else None

    contact = Contact(
        id=data.id if data else None,
        name=name,
        organisationName=org,
        type=ContactType.ORG if org is not None
            else ContactType.PERSON if name is not None
            else ContactType.UNDEFINED,
        email=email,
        phone=_phone(getattr(data, "voice", None)) if data else None,
        fax=_phone(getattr(data, "fax", None)) if data else None,
        address=address,
        # common fields
        status=[s.s.value for s in getattr(data, "status", [])] if data else None,
        crDate=_dt(getattr(data, "cr_date", None)) if data else None,
        exDate=None,
        upDate=_dt(getattr(data, "up_date", None)) if data else None,
        trDate=_dt(getattr(data, "tr_date", None)) if data else None,
        clID=getattr(data, "cl_id", None) if data else None,
        crID=getattr(data, "cr_id", None) if data else None,
        authInfo=AuthInfo(pw=pw, hash=None) if pw is not None else None,
    )

    return ContactCreateResponse(contact=contact, **header)
