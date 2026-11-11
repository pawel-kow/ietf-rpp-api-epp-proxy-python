from typing import Protocol

from core.model.host.host import Host
from core.model.host.host_check_response import HostCheckResponse
from core.model.host.host_create_response import HostCreateResponse
from core.model.host.host_delete_response import HostDeleteResponse
from core.model.host.host_info_response import HostInfoResponse
from core.model.host.host_replacement import HostReplacement
from core.model.host.host_update import HostUpdate
from core.model.host.host_update_response import HostUpdateResponse
from core.result.error_response import ErrorResponse
from core.ports.replace_outcome import ReplaceOutcome


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
