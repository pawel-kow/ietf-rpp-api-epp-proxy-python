from .epp_messages import epp_messages_Ack, epp_messages_Poll
from .eppclient import EPPClient


class EppMessageGateway:
    """The message queue over EPP `<poll>`."""

    def __init__(self, epp_client: EPPClient):
        self._epp_client = epp_client

    def poll(self, client_transaction_id=None):
        return epp_messages_Poll(self._epp_client, client_transaction_id=client_transaction_id)

    def ack(self, message_id, client_transaction_id=None):
        return epp_messages_Ack(self._epp_client, message_id, client_transaction_id=client_transaction_id)
