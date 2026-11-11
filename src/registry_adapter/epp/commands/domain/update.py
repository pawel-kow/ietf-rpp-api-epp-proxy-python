import base64
from typing import Union

from core.model.domain.dns_sec import DnsSec
from core.model.domain.domains import DomainUpdate
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from registry_adapter.epp.commands.domain.common import missing_extension, ns_type
from registry_adapter.epp.commands.shared.epp_core import get_epp_error_response
from registry_adapter.epp.commands.shared.epp_response import cl_trid, parse_epp_response_header
from registry_adapter.epp.session.epp_client import EPPClient, SEC_DNS_EXTENSION
from registry_adapter.epp.xml.codec import epp_to_str, str_to_epp
from registry_adapter.epp.xml.generated.domain_1_0 import (
    AddRemType, AuthInfoChgType, ChgType, ContactAttrType, ContactType, StatusType, StatusValueType, Update,
)
from registry_adapter.epp.xml.generated.epp_1_0 import CommandType, Epp, ExtAnyType, ReadWriteType
from registry_adapter.epp.xml.generated.eppcom_1_0 import PwAuthInfoType
from registry_adapter.epp.xml.generated.sec_dns_1_1 import (
    DsDataType, DsOrKeyType, KeyDataType, RemType as SecdnsRemType, Update as SecdnsUpdateType,
)


def _ds_data(dns_sec: DnsSec) -> list[DsDataType]:
    return [
        DsDataType(key_tag=ds.keyTag, alg=ds.algorithm, digest_type=ds.digestType, digest=bytes.fromhex(ds.digest))
        for ds in dns_sec.ds_data or []
    ]


def _key_data(dns_sec: DnsSec) -> list[KeyDataType]:
    return [
        KeyDataType(flags=key.flags, protocol=key.protocol, alg=key.algorithm, pub_key=base64.b64decode(key.publicKey))
        for key in dns_sec.key_data or []
    ]


def _sec_dns_update(add: DnsSec | None, remove: DnsSec | None) -> SecdnsUpdateType | None:
    if not (add or remove):
        return None
    return SecdnsUpdateType(
        add=DsOrKeyType(ds_data=_ds_data(add), key_data=_key_data(add)) if add else None,
        rem=SecdnsRemType(ds_data=_ds_data(remove), key_data=_key_data(remove)) if remove else None,
    )


def _status_types(labels: list[str] | None, reasons: dict[str, str] | None = None) -> list[StatusType]:
    return [StatusType(s=StatusValueType(label), value=(reasons or {}).get(label, "")) for label in labels or []]


def domain_update(domain_update: DomainUpdate, rpp_cl_trid: str) -> Epp:
    update = Update(name=domain_update.name.upper())

    set_registrant = False
    add = domain_update.add
    remove = domain_update.remove

    if add is not None:
        add_elem = AddRemType()
        if add.contacts is not None:
            for contact in add.contacts:
                if contact.type != "registrant":
                    add_elem.contact.append(
                        ContactType(
                            value=contact.contact.id.upper(),
                            type_value=ContactAttrType(contact.type),
                        )
                    )
                else:
                    set_registrant = True
        if add.ns is not None and (add.ns.host_objs or add.ns.host_attrs):
            add_elem.ns = ns_type(add.ns)
        add_elem.status = _status_types(add.status, add.status_reasons)
        if add_elem.contact or add_elem.ns or add_elem.status:
            update.add = add_elem

    if remove is not None:
        rem_elem = AddRemType()
        if remove.ns is not None and (remove.ns.host_objs or remove.ns.host_attrs):
            rem_elem.ns = ns_type(remove.ns)
        if remove.contacts is not None:
            for contact in remove.contacts:
                if contact.type != "registrant":
                    rem_elem.contact.append(
                        ContactType(
                            value=contact.contact.id.upper(),
                            type_value=ContactAttrType(contact.type),
                        )
                    )
                else:
                    set_registrant = True
        rem_elem.status = _status_types(remove.status)
        if rem_elem.contact or rem_elem.ns or rem_elem.status:
            update.rem = rem_elem

    change = domain_update.change
    if change is not None or set_registrant:
        chg = ChgType()
        if set_registrant:
            # EPP registrant change is a replacement: empty string clears it.
            new_registrant = ""
            if add is not None and add.contacts is not None:
                for contact in add.contacts:
                    if contact.type == "registrant":
                        new_registrant = contact.contact.id.upper()
                        break
            chg.registrant = new_registrant
        if change is not None and change.authInfo is not None and change.authInfo.pw is not None:
            chg.auth_info = AuthInfoChgType(pw=PwAuthInfoType(value=change.authInfo.pw))
        elif change is not None and change.clear_auth_info:
            chg.auth_info = AuthInfoChgType(null="")
        update.chg = chg

    sec_dns = _sec_dns_update(add.dnsSEC if add else None, remove.dnsSEC if remove else None)
    return Epp(
        command=CommandType(
            update=ReadWriteType(other_element=update),
            extension=ExtAnyType(other_element=[sec_dns]) if sec_dns else None,
            cl_trid=rpp_cl_trid,
        )
    )


def create_domain_update_xml(domain_update_model: DomainUpdate, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(domain_update(domain_update_model, cl_trid(client_request_id)), ns_map)


def parse_domain_update_response(xml_string: str, client_transaction_id: str | None) -> Union[OperationResponse[None], ErrorResponse]:
    """Parses an EPP domain update response."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    return OperationResponse(**header)


def epp_domains_Update(epp_client: EPPClient, domain_update: DomainUpdate, client_transaction_id=None, *, ns_map: dict[str, str]) -> Union[OperationResponse[None], ErrorResponse]:
    """
    Updates a domain using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        domain_update (DomainUpdate): The domain update object.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        OperationResponse[Domain]: The response from the EPP server.
    """
    dns_sec = (domain_update.add and domain_update.add.dnsSEC) or (domain_update.remove and domain_update.remove.dnsSEC)
    missing = missing_extension(epp_client, SEC_DNS_EXTENSION, "DNSSEC", dns_sec, client_transaction_id)
    if missing:
        return missing
    eppxml = create_domain_update_xml(domain_update, client_request_id=client_transaction_id, ns_map=ns_map)
    success, code, response = epp_client.send_and_get_response(eppxml)
    
    if success == True:
        domainresp = parse_domain_update_response(response, client_transaction_id=client_transaction_id)
        return domainresp
    else:
        errorresp = get_epp_error_response(response, client_transaction_id=client_transaction_id)
        return errorresp
