from registry_adapter.rri.gateways.rri_contact_gateway import RriContactGateway
from registry_adapter.rri.gateways.rri_domain_gateway import RriDomainGateway
from registry_adapter.rri.gateways.rri_host_gateway import RriHostGateway
from registry_adapter.rri.gateways.rri_message_gateway import RriMessageGateway
from registry_adapter.rri.profile import rri_profile
from registry_adapter.rri.session.rri_client import RriClient


class RriBackend:
    """The registry over one RRI session (a `RegistryBackend`). The sponsor id is the RegAccId of the login, so one
    deployment serves several RegAccs (refactoring.md §3.2)."""

    def __init__(self, rri_client: RriClient, lgr: str | None = None):
        self.rri_client = rri_client
        self.profile = rri_profile(lgr)
        self.domains = RriDomainGateway(rri_client, lgr)
        self.contacts = RriContactGateway(rri_client)
        self.hosts = RriHostGateway()
        self.messages = RriMessageGateway(rri_client)

    @property
    def sponsor_id(self) -> str:
        return self.rri_client.regacc_id

    @property
    def connected(self) -> bool:
        return self.rri_client.connected

    def connect(self) -> None:
        self.rri_client.connect()

    def disconnect(self) -> None:
        self.rri_client.disconnect()

    def verify_credentials(self, user: str, password: str) -> bool:
        return self.rri_client.verify_credentials(user, password)
