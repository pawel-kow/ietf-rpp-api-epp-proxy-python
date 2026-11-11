from typing import Protocol

from models import (
    Contact, ContactCheckResponse, ContactCreateResponse, ContactDeleteResponse, ContactReplacement, ContactTransfer,
    ContactTransferResponse, ContactUpdate, ContactUpdateResponse, ErrorResponse,
)
from .replace_outcome import ReplaceOutcome


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
