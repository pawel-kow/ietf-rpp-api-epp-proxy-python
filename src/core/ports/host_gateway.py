from typing import Protocol

from core.model.host.host import Host
from core.model.host.host_replacement import HostReplacement
from core.model.host.host_update import HostUpdate
from core.model.shared.availability import Availability
from core.ports.replace_outcome import ReplaceOutcome
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse


class HostGateway(Protocol):
    """The host commands of a registry, answering as `DomainGateway` does."""

    def check(self, name: str, client_transaction_id=None) -> OperationResponse[Availability] | ErrorResponse: ...

    def info(self, name: str, client_transaction_id=None) -> OperationResponse[Host] | ErrorResponse: ...

    def create(self, host: Host, client_transaction_id=None) -> OperationResponse[Host] | ErrorResponse: ...

    def update(self, update: HostUpdate, client_transaction_id=None) -> OperationResponse[None] | ErrorResponse:
        """A partial update: only the named changes."""

    def replace(
        self, wanted: HostReplacement, current: OperationResponse[Host] | None = None, client_transaction_id=None,
    ) -> ReplaceOutcome | ErrorResponse:
        """A full update. `current` is a read the caller has made already, so it is not read again."""

    def delete(self, name: str, client_transaction_id=None) -> OperationResponse[None] | ErrorResponse: ...
