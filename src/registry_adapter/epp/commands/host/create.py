from core.model.host.host import Host
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from registry_adapter.epp.commands.host.common import addr_types, header_of, send
from registry_adapter.epp.commands.shared.epp_response import cl_trid, epp_datetime, find_res_data
from registry_adapter.epp.session.epp_client import EPPClient
from registry_adapter.epp.xml.codec import epp_to_str, str_to_epp
from registry_adapter.epp.xml.generated.epp_1_0 import CommandType, Epp, ReadWriteType
from registry_adapter.epp.xml.generated.host_1_0 import Create, CreData


def host_create(host: Host, rpp_cl_trid: str) -> Epp:
    create = Create(name=host.name, addr=addr_types(host.ipv4, host.ipv6))
    return Epp(command=CommandType(create=ReadWriteType(other_element=create), cl_trid=rpp_cl_trid))


def create_host_xml(host: Host, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(host_create(host, cl_trid(client_request_id)), ns_map)


def parse_host_create_response(xml_string: str, client_transaction_id: str | None) -> OperationResponse[Host]:
    """Parses an EPP host create response."""
    epp = str_to_epp(xml_string)
    data = find_res_data(epp, CreData)
    host = Host(name=data.name, crDate=epp_datetime(data.cr_date))
    return OperationResponse(payload=host, **header_of(epp, client_transaction_id))


def epp_hosts_Create(epp_client: EPPClient, host: Host, client_transaction_id=None, *, ns_map: dict[str, str]) -> OperationResponse[Host] | ErrorResponse:
    return send(
        epp_client,
        create_host_xml(host, client_request_id=client_transaction_id, ns_map=ns_map),
        lambda response: parse_host_create_response(response, client_transaction_id),
        client_transaction_id,
    )
