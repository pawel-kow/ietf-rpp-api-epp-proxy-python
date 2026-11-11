from core.model.contact import contact_difference, contact_localization
from core.model.contact.contact_replacement import ContactReplacement
from core.model.contact.contacts import Contact
from core.ports import derived_update
from core.ports.replace_outcome import ReplaceOutcome
from core.ports.replacement_steps import ReplacementSteps
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from registry_adapter.epp import contact_refusal
from registry_adapter.epp.commands.contact.check import epp_contacts_Check
from registry_adapter.epp.commands.contact.create import epp_contacts_Create
from registry_adapter.epp.commands.contact.delete import epp_contacts_Delete
from registry_adapter.epp.commands.contact.info import epp_contacts_Info
from registry_adapter.epp.commands.contact.transfer import epp_contacts_Transfer
from registry_adapter.epp.commands.contact.update import epp_contacts_Update
from registry_adapter.epp.session.epp_client import EPPClient


class EppContactGateway:
    """The contact commands over EPP. EPP has no full update, so `replace` is derived from `<update>`, and refuses
    what RFC 5733 cannot clear."""

    def __init__(self, epp_client: EPPClient, ns_map: dict[str, str]):
        self._epp_client = epp_client
        self._ns_map = ns_map
        self._steps = ReplacementSteps(
            read=self.info,
            prepare=contact_localization.as_stored,
            refuse=contact_refusal.refuse,
            difference=contact_difference.difference,
            changes_nothing=contact_difference.changes_nothing,
            update=self.update,
        )

    def check(self, id, client_transaction_id=None):
        return epp_contacts_Check(self._epp_client, id, client_transaction_id=client_transaction_id, ns_map=self._ns_map)

    def info(self, id, client_transaction_id=None):
        return epp_contacts_Info(self._epp_client, id, client_transaction_id=client_transaction_id, ns_map=self._ns_map)

    def create(self, contact, client_transaction_id=None):
        return epp_contacts_Create(self._epp_client, contact, client_transaction_id=client_transaction_id, ns_map=self._ns_map)

    def update(self, update, client_transaction_id=None):
        return epp_contacts_Update(self._epp_client, update, client_transaction_id=client_transaction_id, ns_map=self._ns_map)

    def replace(
        self, wanted: ContactReplacement, current: OperationResponse[Contact] | None = None, client_transaction_id=None,
    ) -> ReplaceOutcome | ErrorResponse:
        return derived_update.replace(self._steps, wanted.id, wanted, client_transaction_id, current)

    def delete(self, id, client_transaction_id=None):
        return epp_contacts_Delete(self._epp_client, id, client_transaction_id=client_transaction_id, ns_map=self._ns_map)

    def transfer(self, transfer, client_transaction_id=None):
        return epp_contacts_Transfer(self._epp_client, transfer, client_transaction_id=client_transaction_id, ns_map=self._ns_map)
