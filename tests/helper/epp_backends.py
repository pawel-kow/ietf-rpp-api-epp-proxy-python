from registry_adapter.epp.gateways.epp_backend import EppBackend
from tests.helper.epp_ns_map import EPP_NS_MAP


def epp_backends(client_factory):
    """A factory of backends over the EPP clients `client_factory` makes, so a test still sees those clients."""
    return lambda username, password: EppBackend(client_factory(username, password), EPP_NS_MAP)
