from core.model.domain import domain_difference
from core.model.domain.domain_replacement import DomainReplacement
from core.model.domain.domains import Domain
from core.ports import derived_update
from core.ports.replace_outcome import ReplaceOutcome
from core.ports.replacement_steps import ReplacementSteps
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from registry_adapter.epp.commands.domain.check import epp_domains_Check
from registry_adapter.epp.commands.domain.create import epp_domains_Create
from registry_adapter.epp.commands.domain.delete import epp_domains_Delete
from registry_adapter.epp.commands.domain.info import epp_domains_Info, epp_domains_RestoreInfo
from registry_adapter.epp.commands.domain.renew import epp_domains_Renew
from registry_adapter.epp.commands.domain.restore import epp_domains_Restore
from registry_adapter.epp.commands.domain.transfer import epp_domains_Transfer
from registry_adapter.epp.commands.domain.update import epp_domains_Update
from registry_adapter.epp.idn_tables import IdnTables
from registry_adapter.epp.session.epp_client import EPPClient


class EppDomainGateway:
    """The domain commands over EPP. EPP has no full update, so `replace` is derived from `<update>`."""

    def __init__(self, epp_client: EPPClient, ns_map: dict[str, str], idn_tables: IdnTables):
        self._epp_client = epp_client
        self._ns_map = ns_map
        self._idn_tables = idn_tables
        self._steps = ReplacementSteps(
            read=self.info,
            difference=domain_difference.difference,
            changes_nothing=domain_difference.changes_nothing,
            update=self.update,
        )

    def check(self, name, client_transaction_id=None):
        return epp_domains_Check(self._epp_client, name, client_transaction_id=client_transaction_id, ns_map=self._ns_map)

    def info(self, name, client_transaction_id=None):
        return epp_domains_Info(self._epp_client, name, client_transaction_id=client_transaction_id, ns_map=self._ns_map, idn_tables=self._idn_tables)

    def create(self, domain, client_transaction_id=None):
        return epp_domains_Create(self._epp_client, domain, client_transaction_id=client_transaction_id, ns_map=self._ns_map, idn_tables=self._idn_tables)

    def update(self, update, client_transaction_id=None):
        return epp_domains_Update(self._epp_client, update, client_transaction_id=client_transaction_id, ns_map=self._ns_map)

    def replace(
        self, wanted: DomainReplacement, current: OperationResponse[Domain] | None = None, client_transaction_id=None,
    ) -> ReplaceOutcome | ErrorResponse:
        return derived_update.replace(self._steps, wanted.name, wanted, client_transaction_id, current)

    def delete(self, name, client_transaction_id=None):
        return epp_domains_Delete(self._epp_client, name, client_transaction_id=client_transaction_id, ns_map=self._ns_map)

    def transfer(self, transfer, client_transaction_id=None):
        return epp_domains_Transfer(self._epp_client, transfer, client_transaction_id=client_transaction_id, ns_map=self._ns_map)

    def renew(self, renew, client_transaction_id=None):
        return epp_domains_Renew(self._epp_client, renew, client_transaction_id=client_transaction_id, ns_map=self._ns_map)

    def restore(self, restore, client_transaction_id=None):
        return epp_domains_Restore(self._epp_client, restore, client_transaction_id=client_transaction_id, ns_map=self._ns_map)

    def restore_info(self, name, client_transaction_id=None):
        return epp_domains_RestoreInfo(self._epp_client, name, client_transaction_id=client_transaction_id, ns_map=self._ns_map, idn_tables=self._idn_tables)
