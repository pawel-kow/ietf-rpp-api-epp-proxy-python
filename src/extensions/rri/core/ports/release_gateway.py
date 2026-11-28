from typing import Protocol

from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse


class ReleaseGateway(Protocol):
    """The sponsor returns a domain name to the registry, which administers it until another client takes it over."""

    def create(self, name: str, keep_nameservers: bool, client_transaction_id=None) -> OperationResponse[None] | ErrorResponse: ...
