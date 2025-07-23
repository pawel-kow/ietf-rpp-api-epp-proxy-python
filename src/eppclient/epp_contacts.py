from models import *
from epp_to_model_mapper import *
from .eppclient import EPPClient
import os
from typing import Union

#TODO: not tested yet epp_contacts_Create
def epp_contacts_Create(epp_client: EPPClient, contact: Contact, client_transaction_id=None) -> Union[ContactCreateResponse, ErrorResponse]:
    """
    Creates a contact using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        contact (Contact): The contact object to be created.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        ContactCreateResponse: The response from the EPP server.
    """
    eppxml = create_contact_xml(contact, client_request_id=client_transaction_id)
    success, code, response = epp_client.send_and_get_response(eppxml)

    if success == True:
        contactresp = parse_contact_response(response, client_transaction_id=client_transaction_id)
        return contactresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp

#TODO: implement epp_contacts_Info
def epp_contacts_Info(epp_client: EPPClient, id: str, client_transaction_id=None) -> Union[ContactInfoResponse, ErrorResponse]:
    """
    Retrieves information about a contact using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        id (str): The id of the contact to be retrieved.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        DomainInfoResponse: The response from the EPP server.
    """
    eppxml = info_contact_xml(id, client_request_id=client_transaction_id)
    success, code, response = epp_client.send_and_get_response(eppxml)
    
    if success == True:
        contactresp = parse_contact_response(response, client_transaction_id=client_transaction_id)
        return contactresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp

#TODO: implement epp_contacts_Delete
def epp_contacts_Delete(epp_client: EPPClient, id: str, client_transaction_id=None) -> Union[ContactDeleteResponse, ErrorResponse]:
    """
    Deletes a contact using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        id (str): The id of the contact to be deleted.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        DomainDeleteResponse: The response from the EPP server.
    """
    eppxml = delete_contact_xml(id, client_request_id=client_transaction_id)
    success, code, response = epp_client.send_and_get_response(eppxml)
    
    if success == True:
        contactresp = parse_contact_delete_response(response, client_transaction_id=client_transaction_id)
        return contactresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp
