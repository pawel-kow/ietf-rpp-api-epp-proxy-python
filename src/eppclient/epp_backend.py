from .epp_contact_gateway import EppContactGateway
from .epp_domain_gateway import EppDomainGateway
from .epp_host_gateway import EppHostGateway
from .epp_message_gateway import EppMessageGateway
from .eppclient import EPPClient


class EppBackend:
    """The registry over one EPP session (a `RegistryBackend`). The session is the `EPPClient`'s, and the login is
    the `clID` the registry stores as sponsor."""

    def __init__(self, epp_client: EPPClient):
        self.epp_client = epp_client
        self.domains = EppDomainGateway(epp_client)
        self.contacts = EppContactGateway(epp_client)
        self.hosts = EppHostGateway(epp_client)
        self.messages = EppMessageGateway(epp_client)

    @property
    def sponsor_id(self) -> str:
        return self.epp_client.username

    @property
    def connected(self) -> bool:
        return self.epp_client.connected

    def connect(self) -> None:
        self.epp_client.connect()

    def disconnect(self) -> None:
        self.epp_client.disconnect()

    def verify_credentials(self, user: str, password: str) -> bool:
        return self.epp_client.verify_credentials(user, password)
