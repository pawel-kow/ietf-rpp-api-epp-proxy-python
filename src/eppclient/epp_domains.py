from models import *
from epp_to_model_mapper import *
from .eppclient import EPPClient
import os
from typing import Union

def epp_domains_Create(epp_client: EPPClient, domain: Domain, client_transaction_id=None) -> Union[DomainCreateResponse, ErrorResponse]:
    """
    Creates a domain using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        domain (Domain): The domain object to be created.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        DomainCreateResponse: The response from the EPP server.
    """
    eppxml = create_domain_xml(domain, client_request_id=client_transaction_id)
    success, code, response = epp_client.send_and_get_response(eppxml)
    
    if success == True:
        domainresp = parse_domain_response(response, client_transaction_id=client_transaction_id)
        return domainresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp

def epp_domains_Info(epp_client: EPPClient, domain_name: str, client_transaction_id=None) -> Union[DomainInfoResponse, ErrorResponse]:
    """
    Retrieves information about a domain using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        domain_name (str): The name of the domain to be retrieved.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        DomainInfoResponse: The response from the EPP server.
    """
    eppxml = info_domain_xml(domain_name, client_request_id=client_transaction_id)
    success, code, response = epp_client.send_and_get_response(eppxml)
    
    if success == True:
        domainresp = parse_domain_response(response, client_transaction_id=client_transaction_id)
        return domainresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp

def epp_domains_Delete(epp_client: EPPClient, domain_name: str, client_transaction_id=None) -> Union[DomainDeleteResponse, ErrorResponse]:
    """
    Deletes a domain using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        domain_name (str): The name of the domain to be deleted.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        DomainDeleteResponse: The response from the EPP server.
    """
    eppxml = delete_domain_xml(domain_name, client_request_id=client_transaction_id)
    success, code, response = epp_client.send_and_get_response(eppxml)
    
    if success == True:
        domainresp = parse_domain_delete_response(response, client_transaction_id=client_transaction_id)
        return domainresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp

def epp_domains_Check(epp_client: EPPClient, domain_name: str, client_transaction_id=None) -> Union[DomainCheckResponseSingle, ErrorResponse]:
    """
    Deletes a domain using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        domain_name (str): The name of the domain to be deleted.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        DomainDeleteResponse: The response from the EPP server.
    """
    eppxml = domain_check_xml(domain_name, client_request_id=client_transaction_id)
    success, code, response = epp_client.send_and_get_response(eppxml)
    
    if success == True:
        domainresp = parse_domain_check_response_single(response, domain_name, client_transaction_id=client_transaction_id)
        return domainresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp

def epp_domains_Update(epp_client: EPPClient, domain_update: DomainUpdate, client_transaction_id=None) -> Union[DomainCreateResponse, ErrorResponse]:
    """
    Updates a domain using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        domain_update (DomainUpdate): The domain update object.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        DomainCreateResponse: The response from the EPP server.
    """
    eppxml = create_domain_update_xml(domain_update, client_request_id=client_transaction_id)
    success, code, response = epp_client.send_and_get_response(eppxml)
    
    if success == True:
        domainresp = parse_domain_update_response(response, client_transaction_id=client_transaction_id)
        return domainresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp
