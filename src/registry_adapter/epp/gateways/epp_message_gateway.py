from registry_adapter.epp.commands.message.ack import epp_messages_Ack
from registry_adapter.epp.commands.message.poll import epp_messages_Poll
from registry_adapter.epp.session.epp_client import EPPClient


class EppMessageGateway:
    """The message queue over EPP `<poll>`."""

    def __init__(self, epp_client: EPPClient, ns_map: dict[str, str]):
        self._epp_client = epp_client
        self._ns_map = ns_map

    def poll(self, client_transaction_id=None):
        return epp_messages_Poll(self._epp_client, client_transaction_id=client_transaction_id, ns_map=self._ns_map)

    def ack(self, message_id, client_transaction_id=None):
        return epp_messages_Ack(self._epp_client, message_id, client_transaction_id=client_transaction_id, ns_map=self._ns_map)
