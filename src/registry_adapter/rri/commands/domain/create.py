from registry_adapter.rri.commands.domain.common import domain_names, DomainState
from registry_adapter.rri.commands.shared.rri_command import run
from registry_adapter.rri.xml.generated.domain_5_0 import Create


def rri_domain_create(client, name: str, state: DomainState, client_transaction_id=None, n=1):
    return run(client, client_transaction_id, write=True, n=n,
               registry_denic_de_domain_5_0_create=Create(**domain_names(name), contact=state.contacts(),
                                                          dnsentry=state.dnsentries(name)))
