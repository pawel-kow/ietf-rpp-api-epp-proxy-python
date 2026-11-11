from typing import Protocol

from models import AckResponse, ErrorResponse, PollResponse


class MessageGateway(Protocol):
    """The message queue of a registry, answering as `DomainGateway` does."""

    def poll(self, client_transaction_id=None) -> PollResponse | ErrorResponse:
        """The message at the head of the queue, and the size of the queue."""

    def ack(self, message_id: str, client_transaction_id=None) -> AckResponse | ErrorResponse:
        """Removes a message from the queue."""
