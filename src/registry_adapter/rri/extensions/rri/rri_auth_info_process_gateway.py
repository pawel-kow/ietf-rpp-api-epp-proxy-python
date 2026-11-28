from extensions.rri.core.model.auth_info_setting import AuthInfoSetting
from registry_adapter.rri.commands.domain.auth_info import bad_auth_info, valid_auth_info1
from registry_adapter.rri.extensions.rri.commands.auth_info_process.create import rri_auth_info_process_create
from registry_adapter.rri.extensions.rri.commands.auth_info_process.delete import rri_auth_info_process_delete
from registry_adapter.rri.extensions.rri.commands.auth_info_process.info import rri_auth_info_process_info


class RriAuthInfoProcessGateway:
    """The AuthInfo1 of a domain: CREATE-AUTHINFO1, INFO and DELETE-AUTHINFO1."""

    def __init__(self, client):
        self.client = client

    def create(self, setting: AuthInfoSetting, client_transaction_id=None):
        if not valid_auth_info1(setting.password):
            return bad_auth_info(client_transaction_id)
        return rri_auth_info_process_create(self.client, setting, client_transaction_id)

    def info(self, name, client_transaction_id=None):
        return rri_auth_info_process_info(self.client, name, client_transaction_id)

    def delete(self, name, client_transaction_id=None):
        return rri_auth_info_process_delete(self.client, name, client_transaction_id)
