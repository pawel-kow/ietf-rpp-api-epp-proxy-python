from typing import Union

from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from registry_adapter.epp.commands.shared.epp_core import get_epp_error_response
from registry_adapter.epp.commands.shared.epp_response import cl_trid, parse_epp_response_header
from registry_adapter.epp.session.epp_client import EPPClient
from registry_adapter.epp.xml.codec import epp_to_str, str_to_epp
from registry_adapter.epp.xml.generated.domain_1_0 import Delete
from registry_adapter.epp.xml.generated.epp_1_0 import CommandType, Epp, ReadWriteType


def domain_delete(domainname: str, rpp_cl_trid: str) -> Epp:
    return Epp(
        command=CommandType(
            delete=ReadWriteType(other_element=Delete(name=domainname)),
            cl_trid=rpp_cl_trid,
        )
    )


def delete_domain_xml(domain_name: str, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(domain_delete(domain_name, cl_trid(client_request_id)), ns_map)


def parse_domain_delete_response(xml_string: str, client_transaction_id: str) -> Union[OperationResponse[None], ErrorResponse]:
    """Parses an EPP domain delete response."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    return OperationResponse(**header)


def epp_domains_Delete(epp_client: EPPClient, domain_name: str, client_transaction_id=None, *, ns_map: dict[str, str]) -> Union[OperationResponse[None], ErrorResponse]:
    """
    Deletes a domain using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        domain_name (str): The name of the domain to be deleted.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        OperationResponse[None]: The response from the EPP server.
    """
    eppxml = delete_domain_xml(domain_name, client_request_id=client_transaction_id, ns_map=ns_map)
    success, code, response = epp_client.send_and_get_response(eppxml)
    
    if success == True:
        domainresp = parse_domain_delete_response(response, client_transaction_id=client_transaction_id)
        return domainresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp
