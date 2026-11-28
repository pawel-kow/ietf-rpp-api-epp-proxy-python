from extensions.rri.core.model.request_contact import RequestContact
from registry_adapter.rri.commands.contact.common import CONTACT_CODES
from registry_adapter.rri.extensions.rri.commands.request_contact.common import fields_of
from registry_adapter.rri.commands.shared.rri_command import run
from registry_adapter.rri.xml.generated.contact_5_0 import Update


def rri_request_contact_update(client, contact: RequestContact, client_transaction_id=None):
    """UPDATE of a contact of type REQUEST: the whole of it, which is its template."""
    return run(client, client_transaction_id, codes=CONTACT_CODES, write=True, update=Update(**fields_of(contact)))
