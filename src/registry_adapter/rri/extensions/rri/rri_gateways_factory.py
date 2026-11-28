from extensions.rri.core.ports.rri_gateways import RriGateways
from registry_adapter.rri.extensions.rri.rri_request_contact_gateway import RriRequestContactGateway
from registry_adapter.rri.session.rri_client import RriClient


def gateways(client: RriClient) -> RriGateways:
    """The gateways of the rri extension over one RRI session (`RriBackend.extension`)."""
    return RriGateways(request_contacts=RriRequestContactGateway(client))
