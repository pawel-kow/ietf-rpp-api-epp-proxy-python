from typing import Union

from core.model.domain.domain_transfer import DomainTransfer
from core.model.shared.common import AuthInfo
from core.model.shared.domain_transfer_process import DomainTransferProcess
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from registry_adapter.epp.commands.domain.common import period_of
from registry_adapter.epp.commands.shared.epp_core import get_epp_error_response
from registry_adapter.epp.commands.shared.epp_response import (
    cl_trid, epp_datetime, find_res_data, parse_epp_response_header,
)
from registry_adapter.epp.session.epp_client import EPPClient
from registry_adapter.epp.xml.codec import epp_to_str, str_to_epp
from registry_adapter.epp.xml.generated.domain_1_0 import AuthInfoType, Transfer, TrnData
from registry_adapter.epp.xml.generated.epp_1_0 import CommandType, Epp, TransferOpType, TransferType
from registry_adapter.epp.xml.generated.eppcom_1_0 import PwAuthInfoType


def _transfer_auth_info(auth_info: AuthInfo) -> AuthInfoType:
    return AuthInfoType(pw=PwAuthInfoType(value=auth_info.pw, roid=auth_info.roid))


def domain_transfer(transfer: DomainTransfer, rpp_cl_trid: str) -> Epp:
    return Epp(
        command=CommandType(
            transfer=TransferType(
                op=TransferOpType(transfer.operation.value),
                other_element=Transfer(
                    name=transfer.name,
                    period=period_of(transfer.duration) if transfer.duration else None,
                    auth_info=_transfer_auth_info(transfer.authInfo) if transfer.authInfo else None,
                ),
            ),
            cl_trid=rpp_cl_trid,
        )
    )


def transfer_domain_xml(transfer: DomainTransfer, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(domain_transfer(transfer, cl_trid(client_request_id)), ns_map)


def parse_domain_transfer_response(xml_string: str, client_transaction_id: str | None) -> OperationResponse[DomainTransferProcess]:
    """Parses an EPP domain transfer response, which is the same for every operation."""
    epp = str_to_epp(xml_string)
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    data = find_res_data(epp, TrnData)
    if data is None:  # applied, but EPP gave no state
        return OperationResponse(payload=None, **header)
    return OperationResponse(payload=DomainTransferProcess(
            name=data.name,
            trStatus=data.tr_status.value,
            reqClientId=data.re_id,
            requestDate=epp_datetime(data.re_date),
            actClientId=data.ac_id,
            actionDate=epp_datetime(data.ac_date),
            expiryDate=epp_datetime(data.ex_date),
        ), **header)


def epp_domains_Transfer(epp_client: EPPClient, transfer: DomainTransfer, client_transaction_id=None, *, ns_map: dict[str, str]) -> Union[OperationResponse[DomainTransferProcess], ErrorResponse]:
    """
    Runs one operation on the transfer of a domain using EPP commands.
    Args:
        epp_client (EPPClient): The EPP client instance.
        transfer (DomainTransfer): The transfer operation.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        OperationResponse[DomainTransferProcess]: The state of the transfer after the operation.
    """
    eppxml = transfer_domain_xml(transfer, client_request_id=client_transaction_id, ns_map=ns_map)
    success, code, response = epp_client.send_and_get_response(eppxml)

    if success == True:
        return parse_domain_transfer_response(response, client_transaction_id=client_transaction_id)
    else:
        return get_epp_error_response(response, client_transaction_id=client_transaction_id)
