from registry_adapter.rri.commands.message.queue import rri_queue_delete, rri_queue_read


class RriMessageGateway:
    """The message queue of an RRI RegAcc."""

    def __init__(self, client):
        self.client = client

    def poll(self, client_transaction_id=None):
        return rri_queue_read(self.client, client_transaction_id)

    def ack(self, message_id: str, client_transaction_id=None):
        return rri_queue_delete(self.client, message_id, client_transaction_id)
