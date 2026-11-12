from registry_adapter.rri.commands.domain.common import domain_names, DomainState
from registry_adapter.rri.commands.shared.rri_command import run
from registry_adapter.rri.xml.generated.domain_5_0 import Chholder, Update


def rri_domain_update(client, name: str, state: DomainState, client_transaction_id=None, n=1):
    """UPDATE: the full state. What is left out is deleted."""
    return run(client, client_transaction_id, write=True, n=n,
               registry_denic_de_domain_5_0_update=Update(**domain_names(name), contact=state.contacts(),
                                                          dnsentry=state.dnsentries(name)))


def rri_domain_chholder(client, name: str, state: DomainState, client_transaction_id=None, n=1):
    """CHHOLDER: the full state with new holders. It removes every AuthInfo of the domain."""
    return run(client, client_transaction_id, write=True, n=n,
               chholder=Chholder(**domain_names(name), contact=state.contacts(), dnsentry=state.dnsentries(name)))
