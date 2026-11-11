from typing import Union

from xsdata.models.datatype import XmlDate

from core.model.domain.domain_renew import DomainRenew
from core.model.domain.domain_renew_process import DomainRenewProcess
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from core.result.result_code import ResultCode
from registry_adapter.epp.commands.domain.common import period_of
from registry_adapter.epp.commands.shared.epp_core import get_epp_error_response
from registry_adapter.epp.commands.shared.epp_response import (
    cl_trid, epp_datetime, find_res_data, parse_epp_response_header,
)
from registry_adapter.epp.session.epp_client import EPPClient
from registry_adapter.epp.xml.codec import epp_to_str, str_to_epp
from registry_adapter.epp.xml.generated.domain_1_0 import RenData, Renew
from registry_adapter.epp.xml.generated.epp_1_0 import CommandType, Epp, ReadWriteType


def domain_renew(renew: DomainRenew, rpp_cl_trid: str) -> Epp:
    return Epp(
        command=CommandType(
            renew=ReadWriteType(
                other_element=Renew(
                    name=renew.name,
                    cur_exp_date=XmlDate.from_string(renew.curExpDate),
                    period=period_of(renew.duration) if renew.duration else None,
                ),
            ),
            cl_trid=rpp_cl_trid,
        )
    )


def renew_domain_xml(renew: DomainRenew, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(domain_renew(renew, cl_trid(client_request_id)), ns_map)


def parse_domain_renew_response(xml_string: str, client_transaction_id: str | None) -> OperationResponse[DomainRenewProcess]:
    """Parses an EPP domain renew response. A pending renewal has not completed, so it has no new expiry date."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    data = find_res_data(epp, RenData)
    completed = header["code"] != ResultCode.COMMAND_COMPLETED_ACTION_PENDING
    return OperationResponse(payload=DomainRenewProcess(
            name=data.name if data else None,
            expiryDate=epp_datetime(data.ex_date) if data and completed else None,
        ), **header)


def epp_domains_Renew(epp_client: EPPClient, renew: DomainRenew, client_transaction_id=None, *, ns_map: dict[str, str]) -> Union[OperationResponse[DomainRenewProcess], ErrorResponse]:
    """
    Renews a domain using the EPP renew command.
    Args:
        epp_client (EPPClient): The EPP client instance.
        renew (DomainRenew): The renewal, with the current expiry date.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        OperationResponse[DomainRenewProcess]: The new expiry date, when the registry reports it.
    """
    eppxml = renew_domain_xml(renew, client_request_id=client_transaction_id, ns_map=ns_map)
    success, code, response = epp_client.send_and_get_response(eppxml)

    if success == True:
        return parse_domain_renew_response(response, client_transaction_id=client_transaction_id)
    else:
        return get_epp_error_response(response, client_transaction_id=client_transaction_id)
