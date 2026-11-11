from eppclient.epp_backend import EppBackend


def epp_backends(client_factory):
    """A factory of backends over the EPP clients `client_factory` makes, so a test still sees those clients."""
    return lambda username, password: EppBackend(client_factory(username, password))
