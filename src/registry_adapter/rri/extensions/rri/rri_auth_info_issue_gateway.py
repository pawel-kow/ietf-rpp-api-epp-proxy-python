from registry_adapter.rri.extensions.rri.commands.auth_info_issue.create import rri_auth_info_issue_create


class RriAuthInfoIssueGateway:
    """The AuthInfo2 of a domain: CREATE-AUTHINFO2."""

    def __init__(self, client):
        self.client = client

    def create(self, name, client_transaction_id=None):
        return rri_auth_info_issue_create(self.client, name, client_transaction_id)
