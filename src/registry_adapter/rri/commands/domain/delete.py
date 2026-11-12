from registry_adapter.rri.commands.domain.common import domain_names
from registry_adapter.rri.commands.shared.rri_command import run
from registry_adapter.rri.xml.generated.domain_5_0 import Delete


def rri_domain_delete(client, name: str, client_transaction_id=None):
    """DELETE: the domain enters its redemption period."""
    return run(client, client_transaction_id, write=True, delete=Delete(**domain_names(name)))
