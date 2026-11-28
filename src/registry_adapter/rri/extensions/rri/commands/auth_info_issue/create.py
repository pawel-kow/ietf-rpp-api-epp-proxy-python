from registry_adapter.rri.commands.domain.common import domain_names
from registry_adapter.rri.commands.shared.rri_command import run
from registry_adapter.rri.xml.generated.domain_5_0 import CreateAuthInfo2


def rri_auth_info_issue_create(client, name: str, client_transaction_id=None):
    """CREATE-AUTHINFO2: the registry generates the password and posts it to the holders. The reply holds none."""
    return run(client, client_transaction_id, write=True, create_auth_info2=CreateAuthInfo2(**domain_names(name)))
