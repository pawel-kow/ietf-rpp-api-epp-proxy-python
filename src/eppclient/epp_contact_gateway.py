from models import ContactCreateResponse, ContactReplacement, ErrorResponse, contact_difference, contact_localization
from registry import ReplaceOutcome, ReplacementSteps, derived_update
from . import epp_contact_refusal
from .epp_contacts import (
    epp_contacts_Check, epp_contacts_Create, epp_contacts_Delete, epp_contacts_Info, epp_contacts_Transfer,
    epp_contacts_Update,
)
from .eppclient import EPPClient


class EppContactGateway:
    """The contact commands over EPP. EPP has no full update, so `replace` is derived from `<update>`, and refuses
    what RFC 5733 cannot clear."""

    def __init__(self, epp_client: EPPClient):
        self._epp_client = epp_client
        self._steps = ReplacementSteps(
            read=self.info,
            object_of=lambda info: info.contact,
            prepare=contact_localization.as_stored,
            refuse=epp_contact_refusal.refuse,
            difference=contact_difference.difference,
            changes_nothing=contact_difference.changes_nothing,
            update=self.update,
        )

    def check(self, id, client_transaction_id=None):
        return epp_contacts_Check(self._epp_client, id, client_transaction_id=client_transaction_id)

    def info(self, id, client_transaction_id=None):
        return epp_contacts_Info(self._epp_client, id, client_transaction_id=client_transaction_id)

    def create(self, contact, client_transaction_id=None):
        return epp_contacts_Create(self._epp_client, contact, client_transaction_id=client_transaction_id)

    def update(self, update, client_transaction_id=None):
        return epp_contacts_Update(self._epp_client, update, client_transaction_id=client_transaction_id)

    def replace(
        self, wanted: ContactReplacement, current: ContactCreateResponse | None = None, client_transaction_id=None,
    ) -> ReplaceOutcome | ErrorResponse:
        return derived_update.replace(self._steps, wanted.id, wanted, client_transaction_id, current)

    def delete(self, id, client_transaction_id=None):
        return epp_contacts_Delete(self._epp_client, id, client_transaction_id=client_transaction_id)

    def transfer(self, transfer, client_transaction_id=None):
        return epp_contacts_Transfer(self._epp_client, transfer, client_transaction_id=client_transaction_id)
