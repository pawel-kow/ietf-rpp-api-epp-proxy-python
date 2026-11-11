from typing import Callable

from registry_adapter.epp.commands.shared.epp_core import get_epp_error_response
from registry_adapter.epp.commands.shared.epp_response import parse_epp_response_header
from registry_adapter.epp.session.epp_client import EPPClient
from registry_adapter.epp.xml.generated.epp_1_0 import Epp
from registry_adapter.epp.xml.generated.host_1_0 import AddrType, IpType


def addr_types(ipv4: list[str] | None, ipv6: list[str] | None) -> list[AddrType]:
    return [AddrType(value=ip, ip=IpType.V4) for ip in ipv4 or []] + [
        AddrType(value=ip, ip=IpType.V6) for ip in ipv6 or []
    ]


def header_of(epp: Epp, client_transaction_id: str | None) -> dict:
    header = parse_epp_response_header(epp)
    if client_transaction_id is None:
        header["client_transaction_id"] = None
    return header


def send(epp_client: EPPClient, eppxml: str, parse: Callable[[str], object], client_transaction_id):
    """Sends a command and parses the reply, or its error."""
    success, code, response = epp_client.send_and_get_response(eppxml)
    if success:
        return parse(response)
    return get_epp_error_response(response, client_transaction_id=client_transaction_id)
