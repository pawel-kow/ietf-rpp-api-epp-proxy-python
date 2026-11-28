from typing import Protocol

from core.model.message.message_queue import MessageQueue
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse


class MessageGateway(Protocol):
    """The message queue of a registry, answering as `DomainGateway` does."""

    def poll(self, client_transaction_id=None, message_types: tuple[str, ...] | None = None) -> OperationResponse[MessageQueue] | ErrorResponse:
        """The message at the head of the queue, and the size of the queue. `message_types` are the identifiers of the RPP
        message types a client asked for (core §16.10.1): the oldest message of those types, and the number of such messages.
        A backend that cannot select by type ignores them (the EPP Compatibility Profile does)."""

    def find(self, message_id: str, client_transaction_id=None) -> OperationResponse[MessageQueue] | ErrorResponse | None:
        """The message with this id when it is not the head of the queue: the response, an `ErrorResponse` of `OBJECT_DOES_NOT_EXIST`
        where the registry has none, and None where the backend can read only the head."""

    def ack(self, message_id: str, client_transaction_id=None) -> OperationResponse[MessageQueue] | ErrorResponse:
        """Removes a message from the queue."""
