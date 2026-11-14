from registry_adapter.rri.commands.domain.common import domain_names, DomainState
from registry_adapter.rri.commands.shared.rri_command import run
from registry_adapter.rri.xml.generated.domain_5_0 import Chholder, Chprov, Update


def rri_domain_update(client, name: str, state: DomainState, client_transaction_id=None, n=1):
    """UPDATE: the full state. What is left out is deleted."""
    return run(client, client_transaction_id, write=True, n=n,
               registry_denic_de_domain_5_0_update=Update(**domain_names(name), contact=state.contacts(),
                                                          dnsentry=state.dnsentries(name)))


def rri_domain_chholder(client, name: str, state: DomainState, client_transaction_id=None, n=1):
    """CHHOLDER: the full state with new holders. It removes every AuthInfo of the domain."""
    return run(client, client_transaction_id, write=True, n=n,
               chholder=Chholder(**domain_names(name), contact=state.contacts(), dnsentry=state.dnsentries(name)))


def rri_domain_chprov(client, name: str, state: DomainState, auth_info: str, client_transaction_id=None):
    """CHPROV: the full state with the gainer's contacts, and the AuthInfo1 or AuthInfo2 in plaintext, so it is not
    printed. It moves the domain to the requester at once."""
    return run(client, client_transaction_id, write=True, loggable=False,
               chprov=Chprov(**domain_names(name), contact=state.contacts(), dnsentry=state.dnsentries(name),
                             auth_info=auth_info))
