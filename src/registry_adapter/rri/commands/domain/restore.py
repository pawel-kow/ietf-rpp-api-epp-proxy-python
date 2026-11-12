from core.model.domain.domain_restore_process import DomainRestoreProcess
from registry_adapter.rri.commands.domain.common import domain_names
from registry_adapter.rri.commands.shared.rri_command import run
from registry_adapter.rri.xml.generated.domain_5_0 import Restore


def rri_domain_restore(client, name: str, client_transaction_id=None):
    """RESTORE: one step, without a report (gap Q6). The domain is restored when it succeeds."""
    return run(client, client_transaction_id, write=True, payload_of=lambda transaction: DomainRestoreProcess(),
               restore=Restore(**domain_names(name)))
