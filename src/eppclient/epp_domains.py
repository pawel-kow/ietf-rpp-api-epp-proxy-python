from models import *
from epp_to_model_mapper import *
from .eppclient import EPPClient, IDN_EXTENSION, RGP_EXTENSION, SEC_DNS_EXTENSION
import os
from typing import Union

def _missing_extension(epp_client: EPPClient, uri: str, feature: str, data, client_transaction_id) -> ErrorResponse | None:
    """The error for data that needs an extension the server does not offer, or None."""
    if not data or epp_client.supports_extension(uri):
        return None
    return ErrorResponse(
        code=ResultCode.UNIMPLEMENTED_EXTENSION,
        msg=f"{feature} needs {uri}, which the EPP server does not offer",
        server_transaction_id=None,
        client_transaction_id=client_transaction_id,
    )


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
    missing = (
        _missing_extension(epp_client, SEC_DNS_EXTENSION, "DNSSEC", domain.dnsSEC, client_transaction_id)
        or _missing_extension(epp_client, IDN_EXTENSION, "An IDN", domain.idn, client_transaction_id)
    )
    if missing:
        return missing
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

def epp_domains_Update(epp_client: EPPClient, domain_update: DomainUpdate, client_transaction_id=None) -> Union[DomainUpdateResponse, ErrorResponse]:
    """
    Updates a domain using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        domain_update (DomainUpdate): The domain update object.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        DomainCreateResponse: The response from the EPP server.
    """
    dns_sec = (domain_update.add and domain_update.add.dnsSEC) or (domain_update.remove and domain_update.remove.dnsSEC)
    missing = _missing_extension(epp_client, SEC_DNS_EXTENSION, "DNSSEC", dns_sec, client_transaction_id)
    if missing:
        return missing
    eppxml = create_domain_update_xml(domain_update, client_request_id=client_transaction_id)
    success, code, response = epp_client.send_and_get_response(eppxml)
    
    if success == True:
        domainresp = parse_domain_update_response(response, client_transaction_id=client_transaction_id)
        return domainresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp

def epp_domains_Transfer(epp_client: EPPClient, transfer: DomainTransfer, client_transaction_id=None) -> Union[DomainTransferResponse, ErrorResponse]:
    """
    Runs one operation on the transfer of a domain using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        transfer (DomainTransfer): The transfer operation.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        DomainTransferResponse: The state of the transfer after the operation.
    """
    eppxml = transfer_domain_xml(transfer, client_request_id=client_transaction_id)
    success, code, response = epp_client.send_and_get_response(eppxml)

    if success == True:
        return parse_domain_transfer_response(response, client_transaction_id=client_transaction_id)
    else:
        return get_epp_error_response(response, client_transaction_id=client_transaction_id)
def epp_domains_Renew(epp_client: EPPClient, renew: DomainRenew, client_transaction_id=None) -> Union[DomainRenewResponse, ErrorResponse]:
    """
    Renews a domain using the EPP renew command.
    Args:
        epp_client (EPPClient): The EPP client instance.
        renew (DomainRenew): The renewal, with the current expiry date.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        DomainRenewResponse: The new expiry date, when the registry reports it.
    """
    eppxml = renew_domain_xml(renew, client_request_id=client_transaction_id)
    success, code, response = epp_client.send_and_get_response(eppxml)

    if success == True:
        return parse_domain_renew_response(response, client_transaction_id=client_transaction_id)
    else:
        return get_epp_error_response(response, client_transaction_id=client_transaction_id)


def epp_domains_Restore(epp_client: EPPClient, restore: DomainRestore, client_transaction_id=None) -> Union[DomainRestoreResponse, ErrorResponse]:
    """
    Requests the restore of a deleted domain, or sends its report (RFC 3915).
    Args:
        epp_client (EPPClient): The EPP client instance.
        restore (DomainRestore): The request, or the report.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        DomainRestoreResponse: The RGP state of the domain after the command.
    """
    missing = _missing_extension(epp_client, RGP_EXTENSION, "A restore", True, client_transaction_id)
    if missing:
        return missing
    eppxml = restore_domain_xml(restore, client_request_id=client_transaction_id)
    success, code, response = epp_client.send_and_get_response(eppxml)

    if success == True:
        return parse_domain_restore_response(response, restore, client_transaction_id=client_transaction_id)
    else:
        return get_epp_error_response(response, client_transaction_id=client_transaction_id)


def epp_domains_RestoreInfo(epp_client: EPPClient, domain_name: str, client_transaction_id=None) -> Union[DomainInfoResponse, ErrorResponse]:
    """
    Reads a domain for its RGP statuses (RFC 3915 §4.1.2), which a server without the extension does not give.
    Args:
        epp_client (EPPClient): The EPP client instance.
        domain_name (str): The name of the domain.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        DomainInfoResponse: The domain, with its RGP statuses.
    """
    missing = _missing_extension(epp_client, RGP_EXTENSION, "A restore", True, client_transaction_id)
    if missing:
        return missing
    return epp_domains_Info(epp_client, domain_name, client_transaction_id=client_transaction_id)
