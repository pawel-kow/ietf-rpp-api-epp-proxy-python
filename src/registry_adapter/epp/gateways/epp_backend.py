from registry_adapter.epp.gateways.epp_contact_gateway import EppContactGateway
from registry_adapter.epp.gateways.epp_domain_gateway import EppDomainGateway
from registry_adapter.epp.gateways.epp_host_gateway import EppHostGateway
from registry_adapter.epp.gateways.epp_message_gateway import EppMessageGateway
from registry_adapter.epp.profile import EPP_PROFILE
from registry_adapter.epp.session.epp_client import EPPClient


class EppBackend:
    """The registry over one EPP session (a `RegistryBackend`). The session is the `EPPClient`'s, and the login is
    the `clID` the registry stores as sponsor."""

    def __init__(self, epp_client: EPPClient, ns_map: dict[str, str]):
        """
        Args:
            epp_client: The session.
            ns_map: The namespace prefixes the commands are rendered with.
        """
        self.epp_client = epp_client
        self.profile = EPP_PROFILE
        self.domains = EppDomainGateway(epp_client, ns_map)
        self.contacts = EppContactGateway(epp_client, ns_map)
        self.hosts = EppHostGateway(epp_client, ns_map)
        self.messages = EppMessageGateway(epp_client, ns_map)

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
