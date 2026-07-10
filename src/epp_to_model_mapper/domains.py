import uuid
from datetime import timezone
from models import *
from typing import Union
from .epp_core import map_epp_code
from .commands.domains import (
    domain_check,
    domain_create,
    domain_delete,
    domain_info,
    domain_update,
)
from .commands.helper import epp_to_str, str_to_epp
from .epp_model.domain_1_0 import CreData, InfData
from .epp_model.epp_1_0 import Epp


def parse_epp_response_header(epp: Epp) -> dict:
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


def create_domain_xml(domain: Domain, client_request_id=None) -> str:
    return epp_to_str(domain_create(domain, _cl_trid(client_request_id)))


def info_domain_xml(domain_name: str, client_request_id=None) -> str:
    return epp_to_str(domain_info(domain_name, _cl_trid(client_request_id)))


def delete_domain_xml(domain_name: str, client_request_id=None) -> str:
    return epp_to_str(domain_delete(domain_name, _cl_trid(client_request_id)))


def domain_check_xml(domain_name: str, client_request_id=None) -> str:
    return epp_to_str(domain_check(domain_name, _cl_trid(client_request_id)))


def create_domain_update_xml(domain_update_model: DomainUpdate, client_request_id=None) -> str:
    return epp_to_str(domain_update(domain_update_model, _cl_trid(client_request_id)))


def _ns_from_epp(ns) -> Union[NS, None]:
    """Map an EPP domain nsType to the internal NS model."""
    if ns is None:
        return None
    if ns.host_obj:
        return NS(host_objs=[HostObj(id=h) for h in ns.host_obj], host_attrs=None)
    if ns.host_attr:
        host_attrs = [
            HostAttr(
                id=ha.host_name,
                ipv4=[a.value for a in ha.host_addr if a.ip and a.ip.value == "v4"] or None,
                ipv6=[a.value for a in ha.host_addr if a.ip and a.ip.value == "v6"] or None,
            )
            for ha in ns.host_attr
        ]
        return NS(host_objs=None, host_attrs=host_attrs)
    return None


def parse_domain_response(xml_string: str, client_transaction_id: str) -> Union[DomainCreateResponse, ErrorResponse]:
    """Parses an EPP domain create/info response into a DomainCreateResponse."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None

    data = _find_res_data(epp, InfData, CreData)

    registrant = getattr(data, "registrant", None) if data else None

    contacts_dict = {}
    for c in getattr(data, "contact", []) or []:
        role = c.type_value.value if c.type_value else None
        contacts_dict.setdefault(c.value, []).append(role)
    if registrant:
        contacts_dict.setdefault(registrant, []).append("registrant")
    contacts = (
        [ContactReference(types=roles, id=cid) for cid, roles in contacts_dict.items()]
        if contacts_dict
        else None
    )

    auth_info = getattr(data, "auth_info", None) if data else None
    authInfo = None
    if auth_info is not None and auth_info.pw is not None:
        authInfo = AuthInfo(auth_info.pw.value, None)

    ns = _ns_from_epp(getattr(data, "ns", None)) if data else None

    def _dt(value):
        # Emit UTC ISO form with fractional seconds and a trailing "Z"
        # (e.g. "2026-07-10T14:43:55.000000Z"), matching the EPP wire format.
        if value is None:
            return None
        dt = value.to_datetime()
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    domain = Domain(
        name=data.name if data else None,
        crDate=_dt(getattr(data, "cr_date", None)) if data else None,
        exDate=_dt(getattr(data, "ex_date", None)) if data else None,
        upDate=_dt(getattr(data, "up_date", None)) if data else None,
        trDate=_dt(getattr(data, "tr_date", None)) if data else None,
        status=[s.s.value for s in getattr(data, "status", [])] if data else None,
        clID=getattr(data, "cl_id", None) if data else None,
        crID=getattr(data, "cr_id", None) if data else None,
        ns=ns,
        authInfo=authInfo,
        contacts=contacts,
        dnsSEC=None,
    )
    return DomainCreateResponse(domain=domain, **header)


def parse_domain_delete_response(xml_string: str, client_transaction_id: str) -> Union[DomainDeleteResponse, ErrorResponse]:
    """Parses an EPP domain delete response."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    return DomainDeleteResponse(**header)


def parse_domain_update_response(xml_string: str, client_transaction_id: str | None) -> Union[DomainUpdateResponse, ErrorResponse]:
    """Parses an EPP domain update response."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    return DomainUpdateResponse(**header)


def parse_domain_check_response_single(xml_string: str, domain_name: str, client_transaction_id: str) -> Union[DomainCheckResponseSingle, ErrorResponse]:
    response = parse_domain_check_response_bulk(xml_string, client_transaction_id)
    if isinstance(response, DomainCheckResponseBulk):
        if domain_name in response.responses:
            return DomainCheckResponseSingle(
                domain_name=domain_name,
                available=response.responses[domain_name].available,
                reason=response.responses[domain_name].reason,
                code=response.code,
                msg=response.msg,
                server_transaction_id=response.server_transaction_id,
                client_transaction_id=client_transaction_id,
            )
        else:
            return ErrorResponse(
                code=map_epp_code(ResultCode.COMMAND_FAILED.value[0]),
                msg=f"Requested domain name not in the reponse. Original code: {response.code}.",
                server_transaction_id=response.server_transaction_id,
                client_transaction_id=response.client_transaction_id,
            )
    else:
        return response


def parse_domain_check_response_bulk(xml_string: str, client_transaction_id: str) -> Union[DomainCheckResponseBulk, ErrorResponse]:
    epp_response = str_to_epp(xml_string)
    res = DomainCheckResponseBulk(
        **parse_epp_response_header(epp_response),
        responses={},
    )
    for item in epp_response.response.res_data.other_element:
        for check_res in item.cd:
            res.responses[check_res.name.value.lower()] = DomainCheckResponseSingle(
                domain_name=check_res.name.value.lower(),
                available=check_res.name.avail,
                reason=check_res.reason.value if check_res.reason else None,
                **parse_epp_response_header(epp_response),
            )

    return res
