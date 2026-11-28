from core.model.contact.contacts import ContactType
from registry_adapter.rri.commands.contact.common import CONTACT_CODES, fields_of
from registry_adapter.rri.commands.shared.rri_command import run
from registry_adapter.rri.xml.codec import rri_to_str
from registry_adapter.rri.xml.generated.global_5_0 import RegistryRequest
from registry_adapter.rri.xml.generated.contact_5_0 import Update


def rri_contact_update(client, handle: str, contact_type: ContactType, wanted, verification, client_transaction_id=None,
                       extension_fields: dict | None = None):
    """UPDATE: the full contact. What is left out is deleted, so the verification data read before is sent again
    (gap §4.5), unless `extension_fields` (what an extension adds to the command, here the verification information of
    the request) state it. A command that carries verification data is not printed."""
    fields = {"verification_information": list(verification or []), **(extension_fields or {})}
    return run(client, client_transaction_id, codes=CONTACT_CODES, write=True, loggable=not fields["verification_information"],
               update=Update(handle=handle, **fields_of(contact_type, wanted.name, wanted.organisationName, wanted.address,
                                                        wanted.email, wanted.phone), **fields))


def _rendered(handle, contact_type, contact, extension_fields) -> str:
    return rri_to_str(RegistryRequest(update=Update(
        handle=handle.upper(), **fields_of(contact_type, contact.name, contact.organisationName, contact.address,
                                           contact.email, contact.phone), **extension_fields)))


def same_contact(handle: str, contact_type: ContactType, wanted, stored, wanted_fields: dict | None = None,
                 stored_fields: dict | None = None) -> bool:
    """Whether the wanted contact amounts to the UPDATE the stored one does: then nothing need be sent. The fields
    that extensions add (the verification information) are part of it, each side in the same form."""
    return (_rendered(handle, contact_type, wanted, wanted_fields or {})
            == _rendered(handle, contact_type, stored, stored_fields or {}))
