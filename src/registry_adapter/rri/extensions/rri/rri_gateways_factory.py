from extensions.rri.core.ports.rri_gateways import RriGateways
from registry_adapter.rri.extensions.rri.rri_auth_info_issue_gateway import RriAuthInfoIssueGateway
from registry_adapter.rri.extensions.rri.rri_auth_info_process_gateway import RriAuthInfoProcessGateway
from registry_adapter.rri.extensions.rri.rri_release_gateway import RriReleaseGateway
from registry_adapter.rri.extensions.rri.rri_request_contact_gateway import RriRequestContactGateway
from registry_adapter.rri.extensions.rri.rri_verification_process_gateway import RriVerificationProcessGateway
from registry_adapter.rri.session.rri_client import RriClient


def gateways(client: RriClient) -> RriGateways:
    """The gateways of the rri extension over one RRI session (`RriBackend.extension`)."""
    return RriGateways(request_contacts=RriRequestContactGateway(client),
                       auth_info_processes=RriAuthInfoProcessGateway(client),
                       auth_info_issues=RriAuthInfoIssueGateway(client),
                       verification_processes=RriVerificationProcessGateway(client),
                       releases=RriReleaseGateway(client))
