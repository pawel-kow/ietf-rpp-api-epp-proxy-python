from registry_adapter.rri.extensions.rri.commands.release.create import rri_release_create


class RriReleaseGateway:
    """The release of a domain name to the registry: TRANSIT."""

    def __init__(self, client):
        self.client = client

    def create(self, name, keep_nameservers, client_transaction_id=None):
        return rri_release_create(self.client, name, keep_nameservers, client_transaction_id)
