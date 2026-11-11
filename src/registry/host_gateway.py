from typing import Protocol

from models import (
    ErrorResponse, Host, HostCheckResponse, HostCreateResponse, HostDeleteResponse, HostInfoResponse, HostReplacement,
    HostUpdate, HostUpdateResponse,
)
from .replace_outcome import ReplaceOutcome


class HostGateway(Protocol):
    """The host commands of a registry, answering as `DomainGateway` does."""

    def check(self, name: str, client_transaction_id=None) -> HostCheckResponse | ErrorResponse: ...

    def info(self, name: str, client_transaction_id=None) -> HostInfoResponse | ErrorResponse: ...

    def create(self, host: Host, client_transaction_id=None) -> HostCreateResponse | ErrorResponse: ...

    def update(self, update: HostUpdate, client_transaction_id=None) -> HostUpdateResponse | ErrorResponse:
        """A partial update: only the named changes."""

    def replace(
        self, wanted: HostReplacement, current: HostInfoResponse | None = None, client_transaction_id=None,
    ) -> ReplaceOutcome | ErrorResponse:
        """A full update. `current` is a read the caller has made already, so it is not read again."""

    def delete(self, name: str, client_transaction_id=None) -> HostDeleteResponse | ErrorResponse: ...
