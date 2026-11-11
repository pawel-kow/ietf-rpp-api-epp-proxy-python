import base64
from typing import Union

from core.model.domain.dns_sec import DnsSec
from core.model.domain.domains import Domain
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from registry_adapter.epp.commands.domain.common import missing_extension, ns_type, period_of
from registry_adapter.epp.commands.domain.info import parse_domain_response
from registry_adapter.epp.commands.shared.epp_core import get_epp_error_response
from registry_adapter.epp.commands.shared.epp_response import cl_trid
from registry_adapter.epp.idn_tables import IdnTables
from registry_adapter.epp.session.epp_client import EPPClient, IDN_EXTENSION, SEC_DNS_EXTENSION
from registry_adapter.epp.xml.codec import epp_to_str
from registry_adapter.epp.xml.generated.domain_1_0 import AuthInfoType, ContactAttrType, ContactType, Create
from registry_adapter.epp.xml.generated.epp_1_0 import CommandType, Epp, ExtAnyType, ReadWriteType
from registry_adapter.epp.xml.generated.eppcom_1_0 import PwAuthInfoType
from registry_adapter.epp.xml.generated.idn_1_0 import Data as IdnData
from registry_adapter.epp.xml.generated.sec_dns_1_1 import Create as SecdnsCreateType, DsDataType, KeyDataType


def _sec_dns_create(dns_sec: DnsSec) -> SecdnsCreateType:
    return SecdnsCreateType(
        ds_data=[
            DsDataType(key_tag=ds.keyTag, alg=ds.algorithm, digest_type=ds.digestType, digest=bytes.fromhex(ds.digest))
            for ds in dns_sec.ds_data or []
        ],
        key_data=[
            KeyDataType(flags=key.flags, protocol=key.protocol, alg=key.algorithm, pub_key=base64.b64decode(key.publicKey))
            for key in dns_sec.key_data or []
        ],
    )


def domain_create(domain: Domain, rpp_cl_trid: str, idn_tables: IdnTables) -> Epp:
    create = Create(name=domain.name.upper())

    if domain.processes and domain.processes.get("creation"):
        create.period = period_of(domain.processes["creation"].duration)

    if domain.ns and (domain.ns.host_objs or domain.ns.host_attrs):
        create.ns = ns_type(domain.ns)

    if domain.contacts:
        registrant_generated = False
        for contact in domain.contacts:
            if "registrant" in contact.types:
                if registrant_generated:
                    raise ValueError("Only one registrant is allowed in EPP")
                create.registrant = contact.id.upper()
                registrant_generated = True
            for t in contact.types:
                if t != "registrant":
                    create.contact.append(
                        ContactType(value=contact.id.upper(), type_value=ContactAttrType(t))
                    )

    if domain.authInfo and domain.authInfo.pw:
        create.auth_info = AuthInfoType(pw=PwAuthInfoType(value=domain.authInfo.pw))

    extensions = []
    if domain.dnsSEC:
        extensions.append(_sec_dns_create(domain.dnsSEC))
    if domain.idn:
        extensions.append(IdnData(table=idn_tables.table(domain.idn.lgr), uname=domain.idn.uname))

    return Epp(
        command=CommandType(
            create=ReadWriteType(other_element=create),
            extension=ExtAnyType(other_element=extensions) if extensions else None,
            cl_trid=rpp_cl_trid,
        )
    )


def create_domain_xml(domain: Domain, client_request_id=None, *, ns_map: dict[str, str], idn_tables: IdnTables) -> str:
    return epp_to_str(domain_create(domain, cl_trid(client_request_id), idn_tables), ns_map)


def epp_domains_Create(epp_client: EPPClient, domain: Domain, client_transaction_id=None, *, ns_map: dict[str, str], idn_tables: IdnTables) -> Union[OperationResponse[Domain], ErrorResponse]:
    """
    Creates a domain using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        domain (Domain): The domain object to be created.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        OperationResponse[Domain]: The response from the EPP server.
    """
    missing = (
        missing_extension(epp_client, SEC_DNS_EXTENSION, "DNSSEC", domain.dnsSEC, client_transaction_id)
        or missing_extension(epp_client, IDN_EXTENSION, "An IDN", domain.idn, client_transaction_id)
    )
    if missing:
        return missing
    eppxml = create_domain_xml(domain, client_request_id=client_transaction_id, ns_map=ns_map, idn_tables=idn_tables)
    success, code, response = epp_client.send_and_get_response(eppxml)
    
    if success == True:
        domainresp = parse_domain_response(response, client_transaction_id=client_transaction_id, idn_tables=idn_tables)
        return domainresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp
