from typing import Union

from core.model.contact.address import Address
from core.model.contact.contact_update import ContactUpdate
from core.model.contact.contact_update_changes import ContactUpdateChanges
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from registry_adapter.epp.commands.contact.common import e164_of
from registry_adapter.epp.commands.shared.epp_core import get_epp_error_response
from registry_adapter.epp.commands.shared.epp_response import cl_trid, parse_epp_response_header
from registry_adapter.epp.session.epp_client import EPPClient
from registry_adapter.epp.xml.codec import epp_to_str, str_to_epp
from registry_adapter.epp.xml.generated.contact_1_0 import (
    AddRemType, AddrType, AuthInfoType, ChgPostalInfoType, ChgType, PostalInfoEnumType, StatusType, StatusValueType,
    Update,
)
from registry_adapter.epp.xml.generated.epp_1_0 import CommandType, Epp, ReadWriteType
from registry_adapter.epp.xml.generated.eppcom_1_0 import PwAuthInfoType


def _addr_type(address: Address) -> AddrType:
    addr = AddrType(street=list(address.street or []), city=address.city, sp=address.stateProvince, pc=address.postalCode, cc=address.country)
    return addr


def _chg_postal_info(change) -> ChgPostalInfoType:
    """A form of a change. `org` "" clears the organisation."""
    return ChgPostalInfoType(
        type_value=PostalInfoEnumType(change.form),
        name=change.name,
        org=change.organisationName,
        addr=_addr_type(change.address) if change.address else None,
    )


def _chg(change) -> ChgType | None:
    if not change:
        return None
    return ChgType(
        postal_info=[_chg_postal_info(form) for form in change.postal_info],
        voice=e164_of(change.voice) if change.voice is not None else None,
        fax=e164_of(change.fax) if change.fax is not None else None,
        email=change.email,
        auth_info=AuthInfoType(pw=PwAuthInfoType(value=change.authInfo.pw)) if change.authInfo else None,
    )


def _add_rem(changes: ContactUpdateChanges | None) -> AddRemType | None:
    if not changes:
        return None
    return AddRemType(status=[
        StatusType(s=StatusValueType(label), value=changes.status_reasons.get(label, "")) for label in changes.status
    ])


def contact_update(update: ContactUpdate, rpp_cl_trid: str) -> Epp:
    body = Update(id=update.id, add=_add_rem(update.add), rem=_add_rem(update.remove), chg=_chg(update.change))
    return Epp(command=CommandType(update=ReadWriteType(other_element=body), cl_trid=rpp_cl_trid))


def update_contact_xml(update: ContactUpdate, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(contact_update(update, cl_trid(client_request_id)), ns_map)


def parse_contact_update_response(xml_string: str, client_transaction_id: str | None) -> OperationResponse[None]:
    """Parses an EPP contact update response."""
    header = parse_epp_response_header(str_to_epp(xml_string))
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    return OperationResponse(**header)


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
