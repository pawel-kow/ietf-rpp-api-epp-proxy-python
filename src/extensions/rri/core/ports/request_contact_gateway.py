from typing import Protocol

from extensions.rri.core.model.request_contact import RequestContact
from core.model.shared.availability import Availability
from core.ports.replace_outcome import ReplaceOutcome
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse


class RequestContactGateway(Protocol):
    """The request contact commands of a registry, answering as `ContactGateway` does. A backend without request
    contacts answers `UNIMPLEMENTED_COMMAND` to each."""

    def check(self, id: str, client_transaction_id=None) -> OperationResponse[Availability] | ErrorResponse: ...

    def info(self, id: str, client_transaction_id=None) -> OperationResponse[RequestContact] | ErrorResponse: ...

    def create(self, contact: RequestContact, client_transaction_id=None) -> OperationResponse[RequestContact] | ErrorResponse: ...

    def replace(
        self, wanted: RequestContact, current: OperationResponse[RequestContact] | None = None,
        client_transaction_id=None,
    ) -> ReplaceOutcome | ErrorResponse:
        """A full update. `current` is a read the caller has made already, so it is not read again."""

    def delete(self, id: str, client_transaction_id=None) -> OperationResponse[None] | ErrorResponse: ...
