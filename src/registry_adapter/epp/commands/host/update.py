from core.model.host.host_update import HostUpdate
from core.model.host.host_update_changes import HostUpdateChanges
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from registry_adapter.epp.commands.host.common import addr_types, header_of, send
from registry_adapter.epp.commands.shared.epp_response import cl_trid
from registry_adapter.epp.session.epp_client import EPPClient
from registry_adapter.epp.xml.codec import epp_to_str, str_to_epp
from registry_adapter.epp.xml.generated.epp_1_0 import CommandType, Epp, ReadWriteType
from registry_adapter.epp.xml.generated.host_1_0 import AddRemType, ChgType, StatusType, StatusValueType, Update


def _add_rem(changes: HostUpdateChanges | None) -> AddRemType | None:
    if not changes:
        return None
    return AddRemType(
        addr=addr_types(changes.ipv4, changes.ipv6),
        status=[
            StatusType(s=StatusValueType(label), value=changes.status_reasons.get(label, ""))
            for label in changes.status
        ],
    )


def host_update(host_update_model: HostUpdate, rpp_cl_trid: str) -> Epp:
    update = Update(
        name=host_update_model.name,
        add=_add_rem(host_update_model.add),
        rem=_add_rem(host_update_model.remove),
        chg=ChgType(name=host_update_model.new_name) if host_update_model.new_name else None,
    )
    return Epp(command=CommandType(update=ReadWriteType(other_element=update), cl_trid=rpp_cl_trid))


def create_host_update_xml(update: HostUpdate, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(host_update(update, cl_trid(client_request_id)), ns_map)


def parse_host_update_response(xml_string: str, client_transaction_id: str | None) -> OperationResponse[None]:
    """Parses an EPP host update response."""
    return OperationResponse(**header_of(str_to_epp(xml_string), client_transaction_id))


def epp_hosts_Update(epp_client: EPPClient, update: HostUpdate, client_transaction_id=None, *, ns_map: dict[str, str]) -> OperationResponse[None] | ErrorResponse:
    return send(
        epp_client,
        create_host_update_xml(update, client_request_id=client_transaction_id, ns_map=ns_map),
        lambda response: parse_host_update_response(response, client_transaction_id),
        client_transaction_id,
    )
