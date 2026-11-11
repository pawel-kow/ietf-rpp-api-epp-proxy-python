from core.model.contact.contact_transfer import ContactTransfer
from core.model.contact.contact_update import ContactUpdate
from core.model.contact.contacts import Contact
from core.result.error_response import ErrorResponse
from registry_adapter.epp.commands.contact.contact_xml import (
    contact_check_xml, create_contact_xml, delete_contact_xml, info_contact_xml, parse_contact_check_response,
    parse_contact_delete_response, parse_contact_response, parse_contact_transfer_response,
    parse_contact_update_response, transfer_contact_xml, update_contact_xml,
)
from registry_adapter.epp.commands.shared.epp_core import get_epp_error_response
from registry_adapter.epp.session.epp_client import EPPClient
import os
from typing import Union
from core.model.shared.availability import Availability
from core.model.shared.contact_transfer_process import ContactTransferProcess
from core.result.operation_response import OperationResponse

def epp_contacts_Create(epp_client: EPPClient, contact: Contact, client_transaction_id=None, *, ns_map: dict[str, str]) -> Union[OperationResponse[Contact], ErrorResponse]:
    """
    Creates a contact using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        contact (Contact): The contact object to be created.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        OperationResponse[Contact]: The response from the EPP server.
    """
    eppxml = create_contact_xml(contact, client_request_id=client_transaction_id, ns_map=ns_map)
    success, code, response = epp_client.send_and_get_response(eppxml)

    if success == True:
        contactresp = parse_contact_response(response, client_transaction_id=client_transaction_id)
        return contactresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp

def epp_contacts_Info(epp_client: EPPClient, id: str, client_transaction_id=None, *, ns_map: dict[str, str]) -> Union[OperationResponse[Contact], ErrorResponse]:
    """
    Retrieves information about a contact using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        id (str): The id of the contact to be retrieved.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        OperationResponse[Contact]: The response from the EPP server.
    """
    eppxml = info_contact_xml(id, client_request_id=client_transaction_id, ns_map=ns_map)
    success, code, response = epp_client.send_and_get_response(eppxml)
    
    if success == True:
        contactresp = parse_contact_response(response, client_transaction_id=client_transaction_id)
        return contactresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp

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


def epp_contacts_Update(epp_client: EPPClient, update: ContactUpdate, client_transaction_id=None, *, ns_map: dict[str, str]) -> Union[OperationResponse[None], ErrorResponse]:
    """
    Updates a contact using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        update (ContactUpdate): The statuses to add and remove and the data to change.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        OperationResponse[None]: The response from the EPP server.
    """
    eppxml = update_contact_xml(update, client_request_id=client_transaction_id, ns_map=ns_map)
    success, code, response = epp_client.send_and_get_response(eppxml)

    if success == True:
        return parse_contact_update_response(response, client_transaction_id=client_transaction_id)
    else:
        return get_epp_error_response(response, client_transaction_id=client_transaction_id)


def epp_contacts_Transfer(epp_client: EPPClient, transfer: ContactTransfer, client_transaction_id=None, *, ns_map: dict[str, str]) -> Union[OperationResponse[ContactTransferProcess], ErrorResponse]:
    """
    Runs one operation on the transfer of a contact using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        transfer (ContactTransfer): The transfer operation.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        OperationResponse[ContactTransferProcess]: The state of the transfer after the operation.
    """
    eppxml = transfer_contact_xml(transfer, client_request_id=client_transaction_id, ns_map=ns_map)
    success, code, response = epp_client.send_and_get_response(eppxml)

    if success == True:
        return parse_contact_transfer_response(response, client_transaction_id=client_transaction_id)
    else:
        return get_epp_error_response(response, client_transaction_id=client_transaction_id)

def epp_contacts_Check(epp_client: EPPClient, id: str, client_transaction_id=None, *, ns_map: dict[str, str]) -> Union[OperationResponse[Availability], ErrorResponse]:
    """Checks whether a contact id can be created. Returns the check result or the EPP error."""
    eppxml = contact_check_xml(id, client_request_id=client_transaction_id, ns_map=ns_map)
    success, code, response = epp_client.send_and_get_response(eppxml)
    if success:
        return parse_contact_check_response(response, id, client_transaction_id)
    return get_epp_error_response(response, client_transaction_id=client_transaction_id)
