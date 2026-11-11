from dataclasses import dataclass


@dataclass(kw_only=True)
class ContactTransferProcess:
    """The state of the transfer of a contact."""
    id: str
    trStatus: str
    reqClientId: str
    requestDate: str
    actClientId: str
    actionDate: str
