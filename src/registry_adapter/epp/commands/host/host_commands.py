from typing import Callable

from core.model.host.host import Host
from core.model.host.host_update import HostUpdate
from core.model.shared.availability import Availability
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from registry_adapter.epp.commands.host.host_xml import (
    create_host_update_xml, create_host_xml, delete_host_xml, host_check_xml, info_host_xml,
    parse_host_check_response, parse_host_create_response, parse_host_delete_response, parse_host_response,
    parse_host_update_response,
)
from registry_adapter.epp.commands.shared.epp_core import get_epp_error_response
from registry_adapter.epp.session.epp_client import EPPClient


def _send(epp_client: EPPClient, eppxml: str, parse: Callable[[str], object], client_transaction_id):
    """Sends a command and parses the reply, or its error."""
    success, code, response = epp_client.send_and_get_response(eppxml)
    if success:
        return parse(response)
    return get_epp_error_response(response, client_transaction_id=client_transaction_id)


def epp_hosts_Create(epp_client: EPPClient, host: Host, client_transaction_id=None, *, ns_map: dict[str, str]) -> OperationResponse[Host] | ErrorResponse:
    return _send(
        epp_client,
        create_host_xml(host, client_request_id=client_transaction_id, ns_map=ns_map),
        lambda response: parse_host_create_response(response, client_transaction_id),
        client_transaction_id,
    )


def epp_hosts_Info(epp_client: EPPClient, host_name: str, client_transaction_id=None, *, ns_map: dict[str, str]) -> OperationResponse[Host] | ErrorResponse:
    return _send(
        epp_client,
        info_host_xml(host_name, client_request_id=client_transaction_id, ns_map=ns_map),
        lambda response: parse_host_response(response, client_transaction_id),
        client_transaction_id,
    )


def epp_hosts_Delete(epp_client: EPPClient, host_name: str, client_transaction_id=None, *, ns_map: dict[str, str]) -> OperationResponse[None] | ErrorResponse:
    return _send(
        epp_client,
        delete_host_xml(host_name, client_request_id=client_transaction_id, ns_map=ns_map),
        lambda response: parse_host_delete_response(response, client_transaction_id),
        client_transaction_id,
    )


def epp_hosts_Check(epp_client: EPPClient, host_name: str, client_transaction_id=None, *, ns_map: dict[str, str]) -> OperationResponse[Availability] | ErrorResponse:
    return _send(
        epp_client,
        host_check_xml(host_name, client_request_id=client_transaction_id, ns_map=ns_map),
        lambda response: parse_host_check_response(response, host_name, client_transaction_id),
        client_transaction_id,
    )


def epp_hosts_Update(epp_client: EPPClient, update: HostUpdate, client_transaction_id=None, *, ns_map: dict[str, str]) -> OperationResponse[None] | ErrorResponse:
    return _send(
        epp_client,
        create_host_update_xml(update, client_request_id=client_transaction_id, ns_map=ns_map),
        lambda response: parse_host_update_response(response, client_transaction_id),
        client_transaction_id,
    )
