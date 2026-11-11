from typing import Protocol

from core.model.domain.domain_renew import DomainRenew
from core.model.domain.domain_replacement import DomainReplacement
from core.model.domain.domain_restore import DomainRestore
from core.model.domain.domain_transfer import DomainTransfer
from core.model.domain.domains import (Domain, DomainUpdate)
from core.result.error_response import ErrorResponse
from core.ports.replace_outcome import ReplaceOutcome
from core.model.shared.availability import Availability
from core.model.domain.domain_renew_process import DomainRenewProcess
from core.model.domain.domain_restore_process import DomainRestoreProcess
from core.model.shared.domain_transfer_process import DomainTransferProcess
from core.result.operation_response import OperationResponse


class DomainGateway(Protocol):
    """The domain commands of a registry. Every method answers an `OperationResponse` whose payload is what the
    command carries back, or an `ErrorResponse`, and a command the registry lacks answers `UNIMPLEMENTED_COMMAND`."""

    def check(self, name: str, client_transaction_id=None) -> OperationResponse[Availability] | ErrorResponse: ...

    def info(self, name: str, client_transaction_id=None) -> OperationResponse[Domain] | ErrorResponse: ...

    def create(self, domain: Domain, client_transaction_id=None) -> OperationResponse[Domain] | ErrorResponse: ...

    def update(self, update: DomainUpdate, client_transaction_id=None) -> OperationResponse[None] | ErrorResponse:
        """A partial update: only the named changes."""

    def replace(
        self, wanted: DomainReplacement, current: OperationResponse[Domain] | None = None, client_transaction_id=None,
    ) -> ReplaceOutcome | ErrorResponse:
        """A full update. `current` is a read the caller has made already, so it is not read again."""

    def delete(self, name: str, client_transaction_id=None) -> OperationResponse[None] | ErrorResponse: ...

    def transfer(self, transfer: DomainTransfer, client_transaction_id=None) -> OperationResponse[DomainTransferProcess] | ErrorResponse: ...

    def renew(self, renew: DomainRenew, client_transaction_id=None) -> OperationResponse[DomainRenewProcess] | ErrorResponse: ...

    def restore(self, restore: DomainRestore, client_transaction_id=None) -> OperationResponse[DomainRestoreProcess] | ErrorResponse:
        """A restore request or report."""

    def restore_info(self, name: str, client_transaction_id=None) -> OperationResponse[Domain] | ErrorResponse:
        """A read of the domain that shows the state of its restore."""
