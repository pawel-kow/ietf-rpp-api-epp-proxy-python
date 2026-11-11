from core.model.shared.availability import Availability
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from registry_adapter.epp.commands.host.common import header_of, send
from registry_adapter.epp.commands.shared.epp_response import cl_trid, find_res_data
from registry_adapter.epp.session.epp_client import EPPClient
from registry_adapter.epp.xml.codec import epp_to_str, str_to_epp
from registry_adapter.epp.xml.generated.epp_1_0 import CommandType, Epp, ReadWriteType
from registry_adapter.epp.xml.generated.host_1_0 import Check, ChkData


def host_check(host_name: str, rpp_cl_trid: str) -> Epp:
    return Epp(command=CommandType(check=ReadWriteType(other_element=Check(name=[host_name])), cl_trid=rpp_cl_trid))


def host_check_xml(host_name: str, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(host_check(host_name, cl_trid(client_request_id)), ns_map)


def parse_host_check_response(xml_string: str, host_name: str, client_transaction_id: str | None) -> OperationResponse[Availability]:
    """Parses the answer to a single-name check. The backend can change the case of the name."""
    epp = str_to_epp(xml_string)
    result = find_res_data(epp, ChkData).cd[0]
    return OperationResponse(
        payload=Availability(name=host_name, available=result.name.avail, reason=result.reason.value if result.reason else None),
        **header_of(epp, client_transaction_id),
    )


def epp_hosts_Check(epp_client: EPPClient, host_name: str, client_transaction_id=None, *, ns_map: dict[str, str]) -> OperationResponse[Availability] | ErrorResponse:
    return send(
        epp_client,
        host_check_xml(host_name, client_request_id=client_transaction_id, ns_map=ns_map),
        lambda response: parse_host_check_response(response, host_name, client_transaction_id),
        client_transaction_id,
    )
