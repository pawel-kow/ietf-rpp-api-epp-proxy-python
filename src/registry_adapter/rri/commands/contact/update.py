from core.model.contact.contacts import ContactType
from registry_adapter.rri.commands.contact.common import CONTACT_CODES, fields_of
from registry_adapter.rri.commands.shared.rri_command import run
from registry_adapter.rri.xml.codec import rri_to_str
from registry_adapter.rri.xml.generated.global_5_0 import RegistryRequest
from registry_adapter.rri.xml.generated.contact_5_0 import Update


def rri_contact_update(client, handle: str, contact_type: ContactType, wanted, verification, client_transaction_id=None):
    """UPDATE: the full contact. What is left out is deleted, so the verification data read before is sent again
    (gap §4.5)."""
    return run(client, client_transaction_id, codes=CONTACT_CODES, write=True, update=Update(
        handle=handle, **fields_of(contact_type, wanted.name, wanted.organisationName, wanted.address, wanted.email,
                                   wanted.phone),
        verification_information=list(verification or [])))


def _rendered(handle, contact_type, contact) -> str:
    return rri_to_str(RegistryRequest(update=Update(
        handle=handle.upper(), **fields_of(contact_type, contact.name, contact.organisationName, contact.address,
                                           contact.email, contact.phone))))


def same_contact(handle: str, contact_type: ContactType, wanted, stored) -> bool:
    """Whether the wanted contact amounts to the UPDATE the stored one does: then nothing need be sent."""
    return _rendered(handle, contact_type, wanted) == _rendered(handle, contact_type, stored)
