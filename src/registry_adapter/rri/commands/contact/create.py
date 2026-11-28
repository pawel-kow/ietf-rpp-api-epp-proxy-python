from core.model.contact.contacts import Contact
from registry_adapter.rri.commands.contact.common import CONTACT_CODES, fields_of
from registry_adapter.rri.commands.shared.rri_command import run
from registry_adapter.rri.xml.generated.contact_5_0 import Create


def rri_contact_create(client, contact: Contact, client_transaction_id=None, extension_fields: dict | None = None):
    """CREATE. `extension_fields` are the fields of the command that extensions add (the verification information); a command
    that carries them is not printed."""
    extension_fields = extension_fields or {}
    return run(client, client_transaction_id, codes=CONTACT_CODES, write=True,
               loggable=not any(extension_fields.values()), create=Create(
        handle=contact.id, **fields_of(contact.type, contact.name, contact.organisationName, contact.address,
                                       contact.email, contact.phone), **extension_fields))
