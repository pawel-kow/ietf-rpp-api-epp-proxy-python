from core.result.result_code import ResultCode
from registry_adapter.rri.commands.shared.rri_command import refused


class RriHostGateway:
    """RRI has no host objects: a name server is an attribute of a domain. Every host command answers
    `UNIMPLEMENTED_COMMAND`, the port's convention for a command the backend lacks."""

    @staticmethod
    def _lacking(client_transaction_id):
        return refused(ResultCode.UNIMPLEMENTED_COMMAND, "RRI has no host objects", client_transaction_id)

    def check(self, name, client_transaction_id=None):
        return self._lacking(client_transaction_id)

    def info(self, name, client_transaction_id=None):
        return self._lacking(client_transaction_id)

    def create(self, host, client_transaction_id=None):
        return self._lacking(client_transaction_id)

    def update(self, update, client_transaction_id=None):
        return self._lacking(client_transaction_id)

    def replace(self, wanted, current=None, client_transaction_id=None):
        return self._lacking(client_transaction_id)

    def delete(self, name, client_transaction_id=None):
        return self._lacking(client_transaction_id)
