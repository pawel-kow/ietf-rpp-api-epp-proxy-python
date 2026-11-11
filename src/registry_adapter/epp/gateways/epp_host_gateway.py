from core.model.host import host_difference
from core.model.host.host import Host
from core.model.host.host_replacement import HostReplacement
from core.ports import derived_update
from core.ports.replace_outcome import ReplaceOutcome
from core.ports.replacement_steps import ReplacementSteps
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from registry_adapter.epp.commands.host.host_commands import (
    epp_hosts_Check, epp_hosts_Create, epp_hosts_Delete, epp_hosts_Info, epp_hosts_Update,
)
from registry_adapter.epp.session.epp_client import EPPClient


class EppHostGateway:
    """The host commands over EPP. EPP has no full update, so `replace` is derived from `<update>`."""

    def __init__(self, epp_client: EPPClient, ns_map: dict[str, str]):
        self._epp_client = epp_client
        self._ns_map = ns_map
        self._steps = ReplacementSteps(
            read=self.info,
            difference=host_difference.difference,
            changes_nothing=host_difference.changes_nothing,
            update=self.update,
        )

    def check(self, name, client_transaction_id=None):
        return epp_hosts_Check(self._epp_client, name, client_transaction_id=client_transaction_id, ns_map=self._ns_map)

    def info(self, name, client_transaction_id=None):
        return epp_hosts_Info(self._epp_client, name, client_transaction_id=client_transaction_id, ns_map=self._ns_map)

    def create(self, host, client_transaction_id=None):
        return epp_hosts_Create(self._epp_client, host, client_transaction_id=client_transaction_id, ns_map=self._ns_map)

    def update(self, update, client_transaction_id=None):
        return epp_hosts_Update(self._epp_client, update, client_transaction_id=client_transaction_id, ns_map=self._ns_map)

    def replace(
        self, wanted: HostReplacement, current: OperationResponse[Host] | None = None, client_transaction_id=None,
    ) -> ReplaceOutcome | ErrorResponse:
        return derived_update.replace(self._steps, wanted.name, wanted, client_transaction_id, current)

    def delete(self, name, client_transaction_id=None):
        return epp_hosts_Delete(self._epp_client, name, client_transaction_id=client_transaction_id, ns_map=self._ns_map)
