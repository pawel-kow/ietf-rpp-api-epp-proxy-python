from registry_adapter.rri.commands.domain.common import domain_names, domain_from_rri
from registry_adapter.rri.commands.shared.rri_command import data_of, run
from registry_adapter.rri.xml.generated.domain_5_0 import Info, InfoData


def rri_domain_info(client, name: str, client_transaction_id=None, *, lgr: str | None = None):
    """Domain INFO, not recursive: the contacts by handle only."""
    return run(client, client_transaction_id, write=False,
               payload_of=lambda transaction: domain_from_rri(data_of(transaction, InfoData), lgr),
               info_1=Info(**domain_names(name), recursive=False))
