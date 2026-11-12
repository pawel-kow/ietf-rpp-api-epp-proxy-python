from core.model.shared.availability import Availability
from registry_adapter.rri.commands.shared.rri_command import data_of, run
from registry_adapter.rri.xml.generated.contact_5_0 import Check, CheckData, StatusType


def rri_contact_check(client, handle: str, client_transaction_id=None):
    """Contact CHECK, of the RegAcc's own handles only: `free` is available."""
    def payload_of(transaction):
        data = data_of(transaction, CheckData)
        status = data.status if data is not None else None
        available = status == StatusType.FREE
        return Availability(name=handle, available=available,
                            reason=None if available or status is None else f"The contact is {status.value}")
    return run(client, client_transaction_id, write=False, payload_of=payload_of, check=Check(handle=handle))
