from models import ErrorResponse, HostInfoResponse, HostReplacement, host_difference
from registry import ReplaceOutcome, ReplacementSteps, derived_update
from .epp_hosts import epp_hosts_Check, epp_hosts_Create, epp_hosts_Delete, epp_hosts_Info, epp_hosts_Update
from .eppclient import EPPClient


class EppHostGateway:
    """The host commands over EPP. EPP has no full update, so `replace` is derived from `<update>`."""

    def __init__(self, epp_client: EPPClient):
        self._epp_client = epp_client
        self._steps = ReplacementSteps(
            read=self.info,
            object_of=lambda info: info.host,
            difference=host_difference.difference,
            changes_nothing=host_difference.changes_nothing,
            update=self.update,
        )

    def check(self, name, client_transaction_id=None):
        return epp_hosts_Check(self._epp_client, name, client_transaction_id=client_transaction_id)

    def info(self, name, client_transaction_id=None):
        return epp_hosts_Info(self._epp_client, name, client_transaction_id=client_transaction_id)

    def create(self, host, client_transaction_id=None):
        return epp_hosts_Create(self._epp_client, host, client_transaction_id=client_transaction_id)

    def update(self, update, client_transaction_id=None):
        return epp_hosts_Update(self._epp_client, update, client_transaction_id=client_transaction_id)

    def replace(
        self, wanted: HostReplacement, current: HostInfoResponse | None = None, client_transaction_id=None,
    ) -> ReplaceOutcome | ErrorResponse:
        return derived_update.replace(self._steps, wanted.name, wanted, client_transaction_id, current)

    def delete(self, name, client_transaction_id=None):
        return epp_hosts_Delete(self._epp_client, name, client_transaction_id=client_transaction_id)
