from core.model.shared.availability import Availability
from registry_adapter.rri.commands.domain.common import domain_names
from registry_adapter.rri.commands.shared.rri_command import data_of, run
from registry_adapter.rri.xml.generated.domain_5_0 import Check, CheckData, StatusType


def _availability(name: str):
    def payload_of(transaction):
        data = data_of(transaction, CheckData)
        status = data.status if data is not None else None
        available = status == StatusType.FREE
        return Availability(name=name, available=available,
                            reason=None if available or status is None else f"The domain is {status.value}")
    return payload_of


def rri_domain_check(client, name: str, client_transaction_id=None):
    """Domain CHECK: `free` is available, any other status (registered, invalid, in its redemption period) is not."""
    return run(client, client_transaction_id, write=False, payload_of=_availability(name),
               registry_denic_de_domain_5_0_check=Check(**domain_names(name)))
