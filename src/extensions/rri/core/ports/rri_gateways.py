from dataclasses import dataclass

from extensions.rri.core.ports.auth_info_issue_gateway import AuthInfoIssueGateway
from extensions.rri.core.ports.auth_info_process_gateway import AuthInfoProcessGateway
from extensions.rri.core.ports.release_gateway import ReleaseGateway
from extensions.rri.core.ports.request_contact_gateway import RequestContactGateway
from extensions.rri.core.ports.verification_process_gateway import VerificationProcessGateway

EXTENSION_ID = "de.denic.rpp.rri"


@dataclass(frozen=True)
class RriGateways:
    """What a backend that holds the rri extension gives for it (`RegistryBackend.extension(EXTENSION_ID)`)."""
    request_contacts: RequestContactGateway
    auth_info_processes: AuthInfoProcessGateway
    auth_info_issues: AuthInfoIssueGateway
    verification_processes: VerificationProcessGateway
    releases: ReleaseGateway
