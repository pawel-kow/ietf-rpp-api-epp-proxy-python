from typing import Protocol

from core.model.domain.domain_renew import DomainRenew
from core.model.domain.domain_renew_response import DomainRenewResponse
from core.model.domain.domain_replacement import DomainReplacement
from core.model.domain.domain_restore import DomainRestore
from core.model.domain.domain_restore_response import DomainRestoreResponse
from core.model.domain.domain_transfer import DomainTransfer
from core.model.domain.domain_transfer_response import DomainTransferResponse
from core.model.domain.domains import (
    Domain, DomainCheckResponseSingle, DomainCreateResponse, DomainDeleteResponse, DomainInfoResponse, DomainUpdate,
    DomainUpdateResponse,
)
from core.result.error_response import ErrorResponse
from core.ports.replace_outcome import ReplaceOutcome


class DomainGateway(Protocol):
    """The domain commands of a registry. Every method answers the typed response or an `ErrorResponse`, and a
    command the registry lacks answers `UNIMPLEMENTED_COMMAND`."""

    def check(self, name: str, client_transaction_id=None) -> DomainCheckResponseSingle | ErrorResponse: ...

    def info(self, name: str, client_transaction_id=None) -> DomainInfoResponse | ErrorResponse: ...

    def create(self, domain: Domain, client_transaction_id=None) -> DomainCreateResponse | ErrorResponse: ...

    def update(self, update: DomainUpdate, client_transaction_id=None) -> DomainUpdateResponse | ErrorResponse:
        """A partial update: only the named changes."""

    def replace(
        self, wanted: DomainReplacement, current: DomainInfoResponse | None = None, client_transaction_id=None,
    ) -> ReplaceOutcome | ErrorResponse:
        """A full update. `current` is a read the caller has made already, so it is not read again."""

    def delete(self, name: str, client_transaction_id=None) -> DomainDeleteResponse | ErrorResponse: ...

    def transfer(self, transfer: DomainTransfer, client_transaction_id=None) -> DomainTransferResponse | ErrorResponse: ...

    def renew(self, renew: DomainRenew, client_transaction_id=None) -> DomainRenewResponse | ErrorResponse: ...

    def restore(self, restore: DomainRestore, client_transaction_id=None) -> DomainRestoreResponse | ErrorResponse:
        """A restore request or report."""

    def restore_info(self, name: str, client_transaction_id=None) -> DomainInfoResponse | ErrorResponse:
        """A read of the domain that shows the state of its restore."""
