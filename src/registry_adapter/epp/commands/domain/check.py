from typing import Union

from core.model.shared.availability import Availability
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from core.result.result_code import ResultCode
from registry_adapter.epp.commands.shared.epp_core import get_epp_error_response, map_epp_code
from registry_adapter.epp.commands.shared.epp_response import cl_trid, parse_epp_response_header
from registry_adapter.epp.session.epp_client import EPPClient
from registry_adapter.epp.xml.codec import epp_to_str, str_to_epp
from registry_adapter.epp.xml.generated.domain_1_0 import Check
from registry_adapter.epp.xml.generated.epp_1_0 import CommandType, Epp, ReadWriteType


def domain_check(domainname: str, rpp_cl_trid: str) -> Epp:
    epp_request = Epp(
        command=CommandType(
            check=ReadWriteType(other_element=Check(name=[domainname])),
            cl_trid=rpp_cl_trid,
        )
    )

    return epp_request


def domain_check_xml(domain_name: str, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(domain_check(domain_name, cl_trid(client_request_id)), ns_map)


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


def epp_domains_Check(epp_client: EPPClient, domain_name: str, client_transaction_id=None, *, ns_map: dict[str, str]) -> Union[OperationResponse[Availability], ErrorResponse]:
    """
    Deletes a domain using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        domain_name (str): The name of the domain to be deleted.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        OperationResponse[None]: The response from the EPP server.
    """
    eppxml = domain_check_xml(domain_name, client_request_id=client_transaction_id, ns_map=ns_map)
    success, code, response = epp_client.send_and_get_response(eppxml)
    
    if success == True:
        domainresp = parse_domain_check_response_single(response, domain_name, client_transaction_id=client_transaction_id)
        return domainresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp
