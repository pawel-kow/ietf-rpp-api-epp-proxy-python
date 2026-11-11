from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from registry_adapter.epp.commands.host.common import header_of, send
from registry_adapter.epp.commands.shared.epp_response import cl_trid
from registry_adapter.epp.session.epp_client import EPPClient
from registry_adapter.epp.xml.codec import epp_to_str, str_to_epp
from registry_adapter.epp.xml.generated.epp_1_0 import CommandType, Epp, ReadWriteType
from registry_adapter.epp.xml.generated.host_1_0 import Delete


def host_delete(host_name: str, rpp_cl_trid: str) -> Epp:
    return Epp(command=CommandType(delete=ReadWriteType(other_element=Delete(name=host_name)), cl_trid=rpp_cl_trid))


def delete_host_xml(host_name: str, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(host_delete(host_name, cl_trid(client_request_id)), ns_map)


def parse_host_delete_response(xml_string: str, client_transaction_id: str | None) -> OperationResponse[None]:
    """Parses an EPP host delete response."""
    return OperationResponse(**header_of(str_to_epp(xml_string), client_transaction_id))


def epp_hosts_Delete(epp_client: EPPClient, host_name: str, client_transaction_id=None, *, ns_map: dict[str, str]) -> OperationResponse[None] | ErrorResponse:
    return send(
        epp_client,
        delete_host_xml(host_name, client_request_id=client_transaction_id, ns_map=ns_map),
        lambda response: parse_host_delete_response(response, client_transaction_id),
        client_transaction_id,
    )
