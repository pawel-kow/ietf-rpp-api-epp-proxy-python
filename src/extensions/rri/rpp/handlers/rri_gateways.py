from extensions.rri.core.ports.rri_gateways import EXTENSION_ID, RriGateways
from rpp.http.context import get_backend


def gateways() -> RriGateways:
    """The gateways of the rri extension of the request's session."""
    return get_backend().extension(EXTENSION_ID)
