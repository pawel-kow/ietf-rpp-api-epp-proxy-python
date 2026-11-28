from typing import Protocol

from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse


class AuthInfoIssueGateway(Protocol):
    """The registry issues authorisation information for a domain name and delivers it to its registrants."""

    def create(self, name: str, client_transaction_id=None) -> OperationResponse[None] | ErrorResponse: ...
