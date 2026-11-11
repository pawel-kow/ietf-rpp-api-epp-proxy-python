import base64
import logging
from typing import Union

from core.model.domain.dns_sec import DnsSec
from core.model.domain.domain_idn import DomainIdn
from core.model.domain.domain_renew import DomainRenew
from core.model.domain.domain_renew_process import DomainRenewProcess
from core.model.domain.domain_restore import DomainRestore
from core.model.domain.domain_restore_process import DomainRestoreProcess
from core.model.domain.domain_transfer import DomainTransfer
from core.model.domain.domains import ContactReference, Domain, DomainUpdate, HostAttr, HostObj, NS
from core.model.domain.ds_data import DsData
from core.model.domain.key_data import KeyData
from core.model.shared.common import AuthInfo
from core.model.shared.domain_transfer_process import DomainTransferProcess
from core.result.error_response import ErrorResponse
from core.result.result_code import ResultCode
from registry_adapter.epp.commands.shared.epp_core import map_epp_code
from registry_adapter.epp.commands.shared.epp_response import (
    cl_trid, epp_datetime, find_extension, find_res_data, parse_epp_response_header, status_reasons,
)
from registry_adapter.epp.commands.domain.epp_request import (
    domain_check, domain_create, domain_delete, domain_info, domain_renew, domain_restore, domain_transfer,
    domain_update,
)
from registry_adapter.epp.idn_tables import IdnTables
from registry_adapter.epp.xml.codec import epp_to_str, str_to_epp
from registry_adapter.epp.xml.generated.domain_1_0 import CreData, InfData, RenData, TrnData
from registry_adapter.epp.xml.generated.epp_1_0 import Epp
from registry_adapter.epp.xml.generated.idn_1_0 import Data as IdnData
from registry_adapter.epp.xml.generated.rgp_1_0 import InfData as RgpInfData, UpData as RgpUpData
from registry_adapter.epp.xml.generated.sec_dns_1_1 import InfData as SecDnsInfData
from core.model.shared.availability import Availability
from core.result.operation_response import OperationResponse


logger = logging.getLogger(__name__)


def create_domain_xml(domain: Domain, client_request_id=None, *, ns_map: dict[str, str], idn_tables: IdnTables) -> str:
    return epp_to_str(domain_create(domain, cl_trid(client_request_id), idn_tables), ns_map)


def info_domain_xml(domain_name: str, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(domain_info(domain_name, cl_trid(client_request_id)), ns_map)


def delete_domain_xml(domain_name: str, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(domain_delete(domain_name, cl_trid(client_request_id)), ns_map)


def domain_check_xml(domain_name: str, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(domain_check(domain_name, cl_trid(client_request_id)), ns_map)


def create_domain_update_xml(domain_update_model: DomainUpdate, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(domain_update(domain_update_model, cl_trid(client_request_id)), ns_map)


def transfer_domain_xml(transfer: DomainTransfer, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(domain_transfer(transfer, cl_trid(client_request_id)), ns_map)


def renew_domain_xml(renew: DomainRenew, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(domain_renew(renew, cl_trid(client_request_id)), ns_map)


def restore_domain_xml(restore: DomainRestore, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(domain_restore(restore, cl_trid(client_request_id)), ns_map)


def _rgp_status(data) -> list[str]:
    """The RGP statuses of rgp:infData or rgp:upData (RFC 3915 §4.1.2, §4.2.5)."""
    return [status.s.value for status in data.rgp_status if status.s is not None] if data else []


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


def _idn_from_epp(epp: Epp, idn_tables: IdnTables) -> Union[DomainIdn, None]:
    """The IDN data of an Info response (draft-obispo-epp-idn-04). Without an LGR for its table there is none, as json
    §6.4 does not allow `uName` without `lgr`."""
    data = find_extension(epp, IdnData)
    if data is None:
        return None
    lgr = idn_tables.lgr(data.table)
    if lgr is None:
        logger.warning("No LGR is configured for the IDN table '%s', so uName and lgr are left out", data.table)
        return None
    return DomainIdn(lgr=lgr, uname=data.uname)


def parse_domain_response(
    xml_string: str, client_transaction_id: str, *, idn_tables: IdnTables,
) -> Union[OperationResponse[Domain], ErrorResponse]:
    """Parses an EPP domain create/info response: the payload is the domain."""
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
        status_reasons=status_reasons(data) if data else {},
        clID=getattr(data, "cl_id", None) if data else None,
        crID=getattr(data, "cr_id", None) if data else None,
        upID=(getattr(data, "up_id", None) or None) if data else None,
        ns=ns,
        authInfo=authInfo,
        contacts=contacts,
        dnsSEC=_dns_sec_from_epp(epp),
        idn=_idn_from_epp(epp, idn_tables),
        rgpStatus=_rgp_status(find_extension(epp, RgpInfData)),
        subordinateHosts=(getattr(data, "host", None) or None) if data else None,
    )
    return OperationResponse(payload=domain, **header)


def parse_domain_delete_response(xml_string: str, client_transaction_id: str) -> Union[OperationResponse[None], ErrorResponse]:
    """Parses an EPP domain delete response."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    return OperationResponse(**header)


def parse_domain_update_response(xml_string: str, client_transaction_id: str | None) -> Union[OperationResponse[None], ErrorResponse]:
    """Parses an EPP domain update response."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    return OperationResponse(**header)


def parse_domain_transfer_response(xml_string: str, client_transaction_id: str | None) -> OperationResponse[DomainTransferProcess]:
    """Parses an EPP domain transfer response, which is the same for every operation."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    data = find_res_data(epp, TrnData)
    if data is None:  # applied, but EPP gave no state
        return OperationResponse(payload=None, **header)
    return OperationResponse(payload=DomainTransferProcess(
            name=data.name,
            trStatus=data.tr_status.value,
            reqClientId=data.re_id,
            requestDate=epp_datetime(data.re_date),
            actClientId=data.ac_id,
            actionDate=epp_datetime(data.ac_date),
            expiryDate=epp_datetime(data.ex_date),
        ), **header)


def parse_domain_renew_response(xml_string: str, client_transaction_id: str | None) -> OperationResponse[DomainRenewProcess]:
    """Parses an EPP domain renew response. A pending renewal has not completed, so it has no new expiry date."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    data = find_res_data(epp, RenData)
    completed = header["code"] != ResultCode.COMMAND_COMPLETED_ACTION_PENDING
    return OperationResponse(payload=DomainRenewProcess(
            name=data.name if data else None,
            expiryDate=epp_datetime(data.ex_date) if data and completed else None,
        ), **header)


def parse_domain_restore_response(xml_string: str, restore: DomainRestore, client_transaction_id: str | None) -> OperationResponse[DomainRestoreProcess]:
    """Parses the reply to a restore. Without rgp:upData, an accepted request (RFC 3915 §3.2) and a pending report
    leave the domain in pendingRestore, and a completed report restores it."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    up_data = find_extension(epp, RgpUpData)
    if up_data is not None:
        rgp_status = _rgp_status(up_data)
    elif restore.report is None or header["code"] == ResultCode.COMMAND_COMPLETED_ACTION_PENDING:
        rgp_status = ["pendingRestore"]
    else:
        rgp_status = []
    return OperationResponse(payload=DomainRestoreProcess(rgpStatus=rgp_status), **header)


def parse_domain_check_response_single(xml_string: str, domain_name: str, client_transaction_id: str) -> Union[OperationResponse[Availability], ErrorResponse]:
    response = parse_domain_check_response_bulk(xml_string, client_transaction_id)
    if isinstance(response, ErrorResponse):
        return response
    if domain_name not in response.payload:
        return ErrorResponse(
            code=map_epp_code(ResultCode.COMMAND_FAILED.value[0]),
            msg=f"Requested domain name not in the reponse. Original code: {response.code}.",
            server_transaction_id=response.server_transaction_id,
            client_transaction_id=response.client_transaction_id,
        )
    return OperationResponse(
        code=response.code,
        msg=response.msg,
        server_transaction_id=response.server_transaction_id,
        client_transaction_id=client_transaction_id,
        payload=response.payload[domain_name],
    )


def parse_domain_check_response_bulk(xml_string: str, client_transaction_id: str) -> Union[OperationResponse[dict[str, Availability]], ErrorResponse]:
    epp_response = str_to_epp(xml_string)
    availability = {}
    for item in epp_response.response.res_data.other_element:
        for check_res in item.cd:
            availability[check_res.name.value.lower()] = Availability(
                name=check_res.name.value.lower(),
                available=check_res.name.avail,
                reason=check_res.reason.value if check_res.reason else None,
            )
    return OperationResponse(payload=availability, **parse_epp_response_header(epp_response))


