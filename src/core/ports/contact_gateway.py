from typing import Protocol

from core.model.contact.contact_replacement import ContactReplacement
from core.model.contact.contact_transfer import ContactTransfer
from core.model.contact.contact_update import ContactUpdate
from core.model.contact.contacts import Contact
from core.result.error_response import ErrorResponse
from core.ports.replace_outcome import ReplaceOutcome
from core.model.shared.availability import Availability
from core.model.shared.contact_transfer_process import ContactTransferProcess
from core.result.operation_response import OperationResponse


class ContactGateway(Protocol):
    """The contact commands of a registry, answering as `DomainGateway` does."""

    def check(self, id: str, client_transaction_id=None) -> OperationResponse[Availability] | ErrorResponse: ...

    def info(self, id: str, client_transaction_id=None) -> OperationResponse[Contact] | ErrorResponse: ...

    def create(self, contact: Contact, client_transaction_id=None) -> OperationResponse[Contact] | ErrorResponse: ...

    def update(self, update: ContactUpdate, client_transaction_id=None) -> OperationResponse[None] | ErrorResponse:
        """A partial update: only the named changes."""

    def replace(
        self, wanted: ContactReplacement, current: OperationResponse[Contact] | None = None, client_transaction_id=None,
    ) -> ReplaceOutcome | ErrorResponse:
        """A full update. `current` is a read the caller has made already, so it is not read again."""

    def delete(self, id: str, client_transaction_id=None) -> OperationResponse[None] | ErrorResponse: ...

    def transfer(self, transfer: ContactTransfer, client_transaction_id=None) -> OperationResponse[ContactTransferProcess] | ErrorResponse: ...
