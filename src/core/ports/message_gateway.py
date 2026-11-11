from typing import Protocol

from core.model.message.message_queue import MessageQueue
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse


class MessageGateway(Protocol):
    """The message queue of a registry, answering as `DomainGateway` does."""

    def poll(self, client_transaction_id=None) -> OperationResponse[MessageQueue] | ErrorResponse:
        """The message at the head of the queue, and the size of the queue."""

    def ack(self, message_id: str, client_transaction_id=None) -> OperationResponse[MessageQueue] | ErrorResponse:
        """Removes a message from the queue."""
