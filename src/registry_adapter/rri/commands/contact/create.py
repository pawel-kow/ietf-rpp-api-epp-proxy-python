from core.model.contact.contacts import Contact
from registry_adapter.rri.commands.contact.common import fields_of
from registry_adapter.rri.commands.shared.rri_command import run
from registry_adapter.rri.xml.generated.contact_5_0 import Create


def rri_contact_create(client, contact: Contact, client_transaction_id=None):
    return run(client, client_transaction_id, write=True, create=Create(
        handle=contact.id, **fields_of(contact.type, contact.name, contact.organisationName, contact.address,
                                       contact.email, contact.phone)))
