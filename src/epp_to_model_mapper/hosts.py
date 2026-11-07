from models import (
    ErrorResponse, Host, HostCheckResponse, HostCreateResponse, HostDeleteResponse, HostInfoResponse,
    HostUpdate, HostUpdateResponse,
)
from .commands.helper import epp_to_str, str_to_epp
from .commands.hosts import host_check, host_create, host_delete, host_info, host_update
from .epp_model.epp_1_0 import Epp
from .epp_model.host_1_0 import ChkData, CreData, InfData, IpType
from .epp_response import cl_trid, epp_datetime, find_res_data, parse_epp_response_header


def create_host_xml(host: Host, client_request_id=None) -> str:
    return epp_to_str(host_create(host, cl_trid(client_request_id)))


def info_host_xml(host_name: str, client_request_id=None) -> str:
    return epp_to_str(host_info(host_name, cl_trid(client_request_id)))


def delete_host_xml(host_name: str, client_request_id=None) -> str:
    return epp_to_str(host_delete(host_name, cl_trid(client_request_id)))


def host_check_xml(host_name: str, client_request_id=None) -> str:
    return epp_to_str(host_check(host_name, cl_trid(client_request_id)))


def create_host_update_xml(update: HostUpdate, client_request_id=None) -> str:
    return epp_to_str(host_update(update, cl_trid(client_request_id)))


def _header(epp: Epp, client_transaction_id: str | None) -> dict:
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    return header


def _addresses(data: InfData) -> tuple[list[str] | None, list[str] | None]:
    """Sorts addresses by their `ip` attribute. A malformed attribute raises, so no address is lost."""
    addresses = {IpType.V4: [], IpType.V6: []}
    for addr in data.addr:
        addresses[addr.ip].append(addr.value)
    return addresses[IpType.V4] or None, addresses[IpType.V6] or None


def _status_reasons(data: InfData) -> dict[str, str]:
    """The status texts that say something: the backend repeats the label there (#54)."""
    return {s.s.value: s.value for s in data.status if s.value and s.value != s.s.value}


def parse_host_response(xml_string: str, client_transaction_id: str | None) -> HostInfoResponse | ErrorResponse:
    """Parses an EPP host info response."""
    epp = str_to_epp(xml_string)
    data = find_res_data(epp, InfData)
    ipv4, ipv6 = _addresses(data)
    host = Host(
        name=data.name,
        roid=data.roid or None,
        ipv4=ipv4,
        ipv6=ipv6,
        status=[s.s.value for s in data.status],
        status_reasons=_status_reasons(data),
        clID=data.cl_id,
        crID=data.cr_id,
        upID=data.up_id or None,
        crDate=epp_datetime(data.cr_date),
        upDate=epp_datetime(data.up_date),
        trDate=epp_datetime(data.tr_date),
    )
    return HostInfoResponse(host=host, **_header(epp, client_transaction_id))


def parse_host_create_response(xml_string: str, client_transaction_id: str | None) -> HostCreateResponse:
    """Parses an EPP host create response."""
    epp = str_to_epp(xml_string)
    data = find_res_data(epp, CreData)
    host = Host(name=data.name, crDate=epp_datetime(data.cr_date))
    return HostCreateResponse(host=host, **_header(epp, client_transaction_id))


def parse_host_check_response(xml_string: str, host_name: str, client_transaction_id: str | None) -> HostCheckResponse:
    """Parses the answer to a single-name check. The backend can change the case of the name."""
    epp = str_to_epp(xml_string)
    result = find_res_data(epp, ChkData).cd[0]
    return HostCheckResponse(
        host_name=host_name,
        available=result.name.avail,
        reason=result.reason.value if result.reason else None,
        **_header(epp, client_transaction_id),
    )


def parse_host_update_response(xml_string: str, client_transaction_id: str | None) -> HostUpdateResponse:
    """Parses an EPP host update response."""
    return HostUpdateResponse(**_header(str_to_epp(xml_string), client_transaction_id))


def parse_host_delete_response(xml_string: str, client_transaction_id: str | None) -> HostDeleteResponse:
    """Parses an EPP host delete response."""
    return HostDeleteResponse(**_header(str_to_epp(xml_string), client_transaction_id))
