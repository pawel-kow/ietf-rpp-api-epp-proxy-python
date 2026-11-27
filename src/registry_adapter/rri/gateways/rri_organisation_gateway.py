from registry_adapter.rri.commands.organisation.info import rri_organisation_info


class RriOrganisationGateway:
    """The organisations of RRI are the RegAccs: regacc INFO reads any of them. The registry maintains them outside RRI, so
    there is no other command."""

    def __init__(self, client, extension_parts=()):
        self.client = client
        self._parts = tuple(extension_parts)

    def info(self, id, client_transaction_id=None):
        return rri_organisation_info(self.client, id, client_transaction_id, self._parts)
