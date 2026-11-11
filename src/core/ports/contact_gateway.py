from typing import Protocol

from core.model.contact.contact_check_response import ContactCheckResponse
from core.model.contact.contact_replacement import ContactReplacement
from core.model.contact.contact_transfer import ContactTransfer
from core.model.contact.contact_transfer_response import ContactTransferResponse
from core.model.contact.contact_update import ContactUpdate
from core.model.contact.contact_update_response import ContactUpdateResponse
from core.model.contact.contacts import Contact, ContactCreateResponse, ContactDeleteResponse
from core.result.error_response import ErrorResponse
from core.ports.replace_outcome import ReplaceOutcome


class ContactGateway(Protocol):
    """The contact commands of a registry, answering as `DomainGateway` does."""

    def check(self, id: str, client_transaction_id=None) -> ContactCheckResponse | ErrorResponse: ...

    def info(self, id: str, client_transaction_id=None) -> ContactCreateResponse | ErrorResponse: ...

    def create(self, contact: Contact, client_transaction_id=None) -> ContactCreateResponse | ErrorResponse: ...

    def update(self, update: ContactUpdate, client_transaction_id=None) -> ContactUpdateResponse | ErrorResponse:
        """A partial update: only the named changes."""

    def replace(
        self, wanted: ContactReplacement, current: ContactCreateResponse | None = None, client_transaction_id=None,
    ) -> ReplaceOutcome | ErrorResponse:
        """A full update. `current` is a read the caller has made already, so it is not read again."""

    def delete(self, id: str, client_transaction_id=None) -> ContactDeleteResponse | ErrorResponse: ...

    def transfer(self, transfer: ContactTransfer, client_transaction_id=None) -> ContactTransferResponse | ErrorResponse: ...
