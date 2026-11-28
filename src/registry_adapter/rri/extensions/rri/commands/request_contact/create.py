from extensions.rri.core.model.request_contact import RequestContact
from registry_adapter.rri.extensions.rri.commands.request_contact.common import fields_of
from registry_adapter.rri.commands.shared.rri_command import run
from registry_adapter.rri.xml.generated.contact_5_0 import Create


def rri_request_contact_create(client, contact: RequestContact, client_transaction_id=None):
    """CREATE of a contact of type REQUEST. The registry test-expands the template and refuses one it cannot
    (83000000005)."""
    return run(client, client_transaction_id, write=True, create=Create(**fields_of(contact)))
