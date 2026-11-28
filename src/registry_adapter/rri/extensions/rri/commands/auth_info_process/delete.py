from registry_adapter.rri.commands.domain.auth_info import rri_delete_auth_info1


def rri_auth_info_process_delete(client, name: str, client_transaction_id=None):
    """DELETE-AUTHINFO1: 63392068709 (none exists) is 404 by the general table."""
    return rri_delete_auth_info1(client, name, client_transaction_id)
