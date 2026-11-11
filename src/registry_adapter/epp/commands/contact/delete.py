from typing import Union

from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from registry_adapter.epp.commands.shared.epp_core import get_epp_error_response
from registry_adapter.epp.commands.shared.epp_response import cl_trid, parse_epp_response_header
from registry_adapter.epp.session.epp_client import EPPClient
from registry_adapter.epp.xml.codec import epp_to_str, str_to_epp
from registry_adapter.epp.xml.generated.contact_1_0 import Delete
from registry_adapter.epp.xml.generated.epp_1_0 import CommandType, Epp, ReadWriteType


def contact_delete(contact_id: str, rpp_cl_trid: str) -> Epp:
    return Epp(
        command=CommandType(
            delete=ReadWriteType(other_element=Delete(id=contact_id)),
            cl_trid=rpp_cl_trid,
        )
    )


def delete_contact_xml(id: str, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(contact_delete(id, cl_trid(client_request_id)), ns_map)


def parse_contact_delete_response(xml_string: str, client_transaction_id: str) -> Union[OperationResponse[None], ErrorResponse]:
    """Parses an EPP contact delete response."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    return OperationResponse(**header)


def epp_contacts_Delete(epp_client: EPPClient, id: str, client_transaction_id=None, *, ns_map: dict[str, str]) -> Union[OperationResponse[None], ErrorResponse]:
    """
    Deletes a contact using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        id (str): The id of the contact to be deleted.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        OperationResponse[None]: The response from the EPP server.
    """
    eppxml = delete_contact_xml(id, client_request_id=client_transaction_id, ns_map=ns_map)
    success, code, response = epp_client.send_and_get_response(eppxml)
    
    if success == True:
        contactresp = parse_contact_delete_response(response, client_transaction_id=client_transaction_id)
        return contactresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp
