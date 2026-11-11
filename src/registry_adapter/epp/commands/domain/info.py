from typing import Union

from core.model.domain.domains import ContactReference, Domain
from core.model.shared.common import AuthInfo
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from registry_adapter.epp.commands.domain.common import (
    dns_sec_from_epp, idn_from_epp, missing_extension, ns_from_epp, rgp_status_of,
)
from registry_adapter.epp.commands.shared.epp_core import get_epp_error_response
from registry_adapter.epp.commands.shared.epp_response import (
    cl_trid, epp_datetime, find_extension, find_res_data, parse_epp_response_header, status_reasons,
)
from registry_adapter.epp.idn_tables import IdnTables
from registry_adapter.epp.session.epp_client import EPPClient, RGP_EXTENSION
from registry_adapter.epp.xml.codec import epp_to_str, str_to_epp
from registry_adapter.epp.xml.generated.domain_1_0 import CreData, InfData, Info, InfoNameType
from registry_adapter.epp.xml.generated.epp_1_0 import CommandType, Epp, ReadWriteType
from registry_adapter.epp.xml.generated.rgp_1_0 import InfData as RgpInfData


def domain_info(domainname: str, rpp_cl_trid: str) -> Epp:
    return Epp(
        command=CommandType(
            info=ReadWriteType(other_element=Info(name=InfoNameType(value=domainname))),
            cl_trid=rpp_cl_trid,
        )
    )


def info_domain_xml(domain_name: str, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(domain_info(domain_name, cl_trid(client_request_id)), ns_map)


def parse_domain_response(
    xml_string: str, client_transaction_id: str, *, idn_tables: IdnTables,
) -> Union[OperationResponse[Domain], ErrorResponse]:
    """Parses an EPP domain create/info response: the payload is the domain."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None

    data = find_res_data(epp, InfData, CreData)

    registrant = getattr(data, "registrant", None) if data else None

    contacts_dict = {}
    for c in getattr(data, "contact", []) or []:
        role = c.type_value.value if c.type_value else None
        contacts_dict.setdefault(c.value, []).append(role)
    if registrant:
        contacts_dict.setdefault(registrant, []).append("registrant")
    contacts = (
        [ContactReference(types=roles, id=cid) for cid, roles in contacts_dict.items()]
        if contacts_dict
        else None
    )

    auth_info = getattr(data, "auth_info", None) if data else None
    authInfo = None
    if auth_info is not None and auth_info.pw is not None:
        authInfo = AuthInfo(auth_info.pw.value, None)

    ns = ns_from_epp(getattr(data, "ns", None)) if data else None

    domain = Domain(
        name=data.name if data else None,
        roid=(getattr(data, "roid", None) or None) if data else None,
        crDate=epp_datetime(getattr(data, "cr_date", None)) if data else None,
        exDate=epp_datetime(getattr(data, "ex_date", None)) if data else None,
        upDate=epp_datetime(getattr(data, "up_date", None)) if data else None,
        trDate=epp_datetime(getattr(data, "tr_date", None)) if data else None,
        status=[s.s.value for s in getattr(data, "status", [])] if data else None,
        status_reasons=status_reasons(data) if data else {},
        clID=getattr(data, "cl_id", None) if data else None,
        crID=getattr(data, "cr_id", None) if data else None,
        upID=(getattr(data, "up_id", None) or None) if data else None,
        ns=ns,
        authInfo=authInfo,
        contacts=contacts,
        dnsSEC=dns_sec_from_epp(epp),
        idn=idn_from_epp(epp, idn_tables),
        rgpStatus=rgp_status_of(find_extension(epp, RgpInfData)),
        subordinateHosts=(getattr(data, "host", None) or None) if data else None,
    )
    return OperationResponse(payload=domain, **header)


def epp_domains_Info(epp_client: EPPClient, domain_name: str, client_transaction_id=None, *, ns_map: dict[str, str], idn_tables: IdnTables) -> Union[OperationResponse[Domain], ErrorResponse]:
    """
    Retrieves information about a domain using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        domain_name (str): The name of the domain to be retrieved.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        OperationResponse[Domain]: The response from the EPP server.
    """
    eppxml = info_domain_xml(domain_name, client_request_id=client_transaction_id, ns_map=ns_map)
    success, code, response = epp_client.send_and_get_response(eppxml)
    
    if success == True:
        domainresp = parse_domain_response(response, client_transaction_id=client_transaction_id, idn_tables=idn_tables)
        return domainresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp


def epp_domains_RestoreInfo(epp_client: EPPClient, domain_name: str, client_transaction_id=None, *, ns_map: dict[str, str], idn_tables: IdnTables) -> Union[OperationResponse[Domain], ErrorResponse]:
    """
    Reads a domain for its RGP statuses (RFC 3915 §4.1.2), which a server without the extension does not give.
    Args:
        epp_client (EPPClient): The EPP client instance.
        domain_name (str): The name of the domain.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        OperationResponse[Domain]: The domain, with its RGP statuses.
    """
    missing = missing_extension(epp_client, RGP_EXTENSION, "A restore", True, client_transaction_id)
    if missing:
        return missing
    return epp_domains_Info(
        epp_client, domain_name, client_transaction_id=client_transaction_id, ns_map=ns_map, idn_tables=idn_tables,
    )
