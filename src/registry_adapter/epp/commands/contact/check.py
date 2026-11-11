from typing import Union

from core.model.shared.availability import Availability
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from registry_adapter.epp.commands.shared.epp_core import get_epp_error_response
from registry_adapter.epp.commands.shared.epp_response import cl_trid, find_res_data, parse_epp_response_header
from registry_adapter.epp.session.epp_client import EPPClient
from registry_adapter.epp.xml.codec import epp_to_str, str_to_epp
from registry_adapter.epp.xml.generated.contact_1_0 import Check, ChkData
from registry_adapter.epp.xml.generated.epp_1_0 import CommandType, Epp, ReadWriteType


def contact_check(contact_id: str, rpp_cl_trid: str) -> Epp:
    return Epp(command=CommandType(check=ReadWriteType(other_element=Check(id=[contact_id.upper()])), cl_trid=rpp_cl_trid))


def contact_check_xml(id: str, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(contact_check(id, cl_trid(client_request_id)), ns_map)


def parse_contact_check_response(xml_string: str, contact_id: str, client_transaction_id: str | None) -> OperationResponse[Availability]:
    """Parses the answer to a single-id check. The backend can change the case of the id."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    result = find_res_data(epp, ChkData).cd[0]
    return OperationResponse(
        payload=Availability(name=contact_id, available=result.id.avail, reason=result.reason.value if result.reason else None),
        **header,
    )


def epp_contacts_Check(epp_client: EPPClient, id: str, client_transaction_id=None, *, ns_map: dict[str, str]) -> Union[OperationResponse[Availability], ErrorResponse]:
    """Checks whether a contact id can be created. Returns the check result or the EPP error."""
    eppxml = contact_check_xml(id, client_request_id=client_transaction_id, ns_map=ns_map)
    success, code, response = epp_client.send_and_get_response(eppxml)
    if success:
        return parse_contact_check_response(response, id, client_transaction_id)
    return get_epp_error_response(response, client_transaction_id=client_transaction_id)
