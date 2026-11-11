from typing import Protocol

from .contact_gateway import ContactGateway
from .domain_gateway import DomainGateway
from .host_gateway import HostGateway
from .message_gateway import MessageGateway


class RegistryBackend(Protocol):
    """One user's session with the registry, which every request of that user works with.

    `sponsor_id` is the id the registry stores as the sponsor of what this user creates.
    """
    domains: DomainGateway
    contacts: ContactGateway
    hosts: HostGateway
    messages: MessageGateway

    @property
    def sponsor_id(self) -> str: ...

    @property
    def connected(self) -> bool: ...

    def connect(self) -> None:
        """Opens the session. `connected` tells whether it succeeded."""

    def disconnect(self) -> None: ...

    def verify_credentials(self, user: str, password: str) -> bool:
        """Whether the credentials are those the session was opened with."""
