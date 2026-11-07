import base64
from typing import Union

from models import *
from .epp_core import map_epp_code
from .epp_response import cl_trid, epp_datetime, find_extension, find_res_data, parse_epp_response_header
from .commands.domains import (
    domain_check,
    domain_create,
    domain_delete,
    domain_info,
    domain_renew,
    domain_transfer,
    domain_update,
)
from .commands.helper import epp_to_str, str_to_epp
from .epp_model.domain_1_0 import CreData, InfData, RenData, TrnData
from .epp_model.epp_1_0 import Epp
from .epp_model.sec_dns_1_1 import InfData as SecDnsInfData


def create_domain_xml(domain: Domain, client_request_id=None) -> str:
    return epp_to_str(domain_create(domain, cl_trid(client_request_id)))


def info_domain_xml(domain_name: str, client_request_id=None) -> str:
    return epp_to_str(domain_info(domain_name, cl_trid(client_request_id)))


def delete_domain_xml(domain_name: str, client_request_id=None) -> str:
    return epp_to_str(domain_delete(domain_name, cl_trid(client_request_id)))


def domain_check_xml(domain_name: str, client_request_id=None) -> str:
    return epp_to_str(domain_check(domain_name, cl_trid(client_request_id)))


def create_domain_update_xml(domain_update_model: DomainUpdate, client_request_id=None) -> str:
    return epp_to_str(domain_update(domain_update_model, cl_trid(client_request_id)))


def transfer_domain_xml(transfer: DomainTransfer, client_request_id=None) -> str:
    return epp_to_str(domain_transfer(transfer, cl_trid(client_request_id)))


def renew_domain_xml(renew: DomainRenew, client_request_id=None) -> str:
    return epp_to_str(domain_renew(renew, cl_trid(client_request_id)))


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


def _dns_sec_from_epp(epp: Epp) -> Union[DnsSec, None]:
    """The DNSSEC data of an Info response. A keyData inside a dsData is not kept (spec-issues.md)."""
    data = find_extension(epp, SecDnsInfData)
    if data is None or not (data.ds_data or data.key_data):
        return None
    return DnsSec(
        ds_data=[
            DsData(keyTag=ds.key_tag, algorithm=ds.alg, digestType=ds.digest_type, digest=ds.digest.hex().upper())
            for ds in data.ds_data
        ] or None,
        key_data=[
            KeyData(
                flags=key.flags,
                protocol=key.protocol,
                algorithm=key.alg,
                publicKey=base64.b64encode(key.pub_key).decode(),
            )
            for key in data.key_data
        ] or None,
    )


def parse_domain_response(xml_string: str, client_transaction_id: str) -> Union[DomainCreateResponse, ErrorResponse]:
    """Parses an EPP domain create/info response into a DomainCreateResponse."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None

    data = find_res_data(epp, InfData, CreData)

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

    domain = Domain(
        name=data.name if data else None,
        roid=(getattr(data, "roid", None) or None) if data else None,
        crDate=epp_datetime(getattr(data, "cr_date", None)) if data else None,
        exDate=epp_datetime(getattr(data, "ex_date", None)) if data else None,
        upDate=epp_datetime(getattr(data, "up_date", None)) if data else None,
        trDate=epp_datetime(getattr(data, "tr_date", None)) if data else None,
        status=[s.s.value for s in getattr(data, "status", [])] if data else None,
        clID=getattr(data, "cl_id", None) if data else None,
        crID=getattr(data, "cr_id", None) if data else None,
        upID=(getattr(data, "up_id", None) or None) if data else None,
        ns=ns,
        authInfo=authInfo,
        contacts=contacts,
        dnsSEC=_dns_sec_from_epp(epp),
        subordinateHosts=(getattr(data, "host", None) or None) if data else None,
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


def parse_domain_transfer_response(xml_string: str, client_transaction_id: str | None) -> DomainTransferResponse:
    """Parses an EPP domain transfer response, which is the same for every operation."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    data = find_res_data(epp, TrnData)
    return DomainTransferResponse(
        transfer=DomainTransferProcess(
            name=data.name,
            trStatus=data.tr_status.value,
            reqClientId=data.re_id,
            requestDate=epp_datetime(data.re_date),
            actClientId=data.ac_id,
            actionDate=epp_datetime(data.ac_date),
            expiryDate=epp_datetime(data.ex_date),
        ),
        **header,
    )


def parse_domain_renew_response(xml_string: str, client_transaction_id: str | None) -> DomainRenewResponse:
    """Parses an EPP domain renew response. A pending renewal has not completed, so it has no new expiry date."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    data = find_res_data(epp, RenData)
    completed = header["code"] != ResultCode.COMMAND_COMPLETED_ACTION_PENDING
    return DomainRenewResponse(
        renewal=DomainRenewProcess(
            name=data.name if data else None,
            expiryDate=epp_datetime(data.ex_date) if data and completed else None,
        ),
        **header,
    )


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


