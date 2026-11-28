from typing import Protocol

from core.model.organisation.organisation import Organisation
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse


class OrganisationGateway(Protocol):
    """The organisation commands of a registry, answering as `DomainGateway` does. Only the read exists: a registry that
    publishes organisations maintains them outside the protocol."""

    def info(self, id: str, client_transaction_id=None) -> OperationResponse[Organisation] | ErrorResponse: ...
