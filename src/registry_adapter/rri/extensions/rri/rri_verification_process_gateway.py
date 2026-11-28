from core.model.shared.common import AuthInfo
from registry_adapter.rri.extensions.rri.commands.verification_process.info import rri_verification_process_info


class RriVerificationProcessGateway:
    """The verification of the holders of a domain name: a recursive domain INFO."""

    def __init__(self, client):
        self.client = client

    def info(self, name: str, authorization: AuthInfo | None = None, client_transaction_id=None):
        return rri_verification_process_info(self.client, name, authorization, client_transaction_id)
