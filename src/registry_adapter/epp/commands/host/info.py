from core.model.host.host import Host
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from registry_adapter.epp.commands.host.common import header_of, send
from registry_adapter.epp.commands.shared.epp_response import cl_trid, epp_datetime, find_res_data, status_reasons
from registry_adapter.epp.session.epp_client import EPPClient
from registry_adapter.epp.xml.codec import epp_to_str, str_to_epp
from registry_adapter.epp.xml.generated.epp_1_0 import CommandType, Epp, ReadWriteType
from registry_adapter.epp.xml.generated.host_1_0 import InfData, Info, IpType


def host_info(host_name: str, rpp_cl_trid: str) -> Epp:
    return Epp(command=CommandType(info=ReadWriteType(other_element=Info(name=host_name)), cl_trid=rpp_cl_trid))


def info_host_xml(host_name: str, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(host_info(host_name, cl_trid(client_request_id)), ns_map)


def _addresses(data: InfData) -> tuple[list[str] | None, list[str] | None]:
    """Sorts addresses by their `ip` attribute. A malformed attribute raises, so no address is lost."""
    addresses = {IpType.V4: [], IpType.V6: []}
    for addr in data.addr:
        addresses[addr.ip].append(addr.value)
    return addresses[IpType.V4] or None, addresses[IpType.V6] or None


def parse_host_response(xml_string: str, client_transaction_id: str | None) -> OperationResponse[Host] | ErrorResponse:
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
        status_reasons=status_reasons(data),
        clID=data.cl_id,
        crID=data.cr_id,
        upID=data.up_id or None,
        crDate=epp_datetime(data.cr_date),
        upDate=epp_datetime(data.up_date),
        trDate=epp_datetime(data.tr_date),
    )
    return OperationResponse(payload=host, **header_of(epp, client_transaction_id))


def epp_hosts_Info(epp_client: EPPClient, host_name: str, client_transaction_id=None, *, ns_map: dict[str, str]) -> OperationResponse[Host] | ErrorResponse:
    return send(
        epp_client,
        info_host_xml(host_name, client_request_id=client_transaction_id, ns_map=ns_map),
        lambda response: parse_host_response(response, client_transaction_id),
        client_transaction_id,
    )
