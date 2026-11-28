from core.capabilities.backend_profile import BackendProfile
from registry_adapter.rri.extension_part import RriExtensionPart
from registry_adapter.rri.gateways.rri_contact_gateway import RriContactGateway
from registry_adapter.rri.gateways.rri_domain_gateway import RriDomainGateway
from registry_adapter.rri.gateways.rri_host_gateway import RriHostGateway
from registry_adapter.rri.gateways.rri_message_gateway import RriMessageGateway
from registry_adapter.rri.gateways.rri_organisation_gateway import RriOrganisationGateway
from registry_adapter.rri.session.rri_client import RriClient


class RriBackend:
    """The registry over one RRI session (a `RegistryBackend`). The sponsor id is the RegAccId of the login, so one
    deployment serves several RegAccs (refactoring.md §3.2)."""

    def __init__(self, rri_client: RriClient, profile: BackendProfile, lgr: str | None = None,
                 extension_parts: list[RriExtensionPart] = ()):
        self.rri_client = rri_client
        self.profile = profile
        self.domains = RriDomainGateway(rri_client, lgr)
        self.contacts = RriContactGateway(rri_client, extension_parts)
        self.hosts = RriHostGateway()
        self.messages = RriMessageGateway(rri_client, extension_parts)
        self.organisations = RriOrganisationGateway(rri_client, extension_parts)
        self._extensions = {part.extension_id: part.gateways(rri_client) for part in extension_parts}

    @property
    def sponsor_id(self) -> str:
        return self.rri_client.regacc_id

    @property
    def connected(self) -> bool:
        return self.rri_client.connected

    def extension(self, extension_id: str):
        return self._extensions[extension_id]

    def connect(self) -> None:
        self.rri_client.connect()

    def disconnect(self) -> None:
        self.rri_client.disconnect()

    def verify_credentials(self, user: str, password: str) -> bool:
        return self.rri_client.verify_credentials(user, password)
