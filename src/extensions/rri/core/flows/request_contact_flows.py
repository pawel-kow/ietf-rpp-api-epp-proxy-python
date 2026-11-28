from typing import Callable

from core.flows.mutation_result import MutationResult
from core.flows.read_back import read_back
from core.flows.sponsor import require_sponsor
from extensions.rri.core.model.request_contact import RequestContact
from extensions.rri.core.ports.rri_gateways import EXTENSION_ID, RriGateways
from core.ports.registry_backend import RegistryBackend
from core.result.error_response import ErrorResponse

OBJECT = "request contact"


def _gateways(backend: RegistryBackend) -> RriGateways:
    return backend.extension(EXTENSION_ID)


def _read_back(backend: RegistryBackend, contact_id: str, mutation) -> MutationResult:
    return read_back(_gateways(backend).request_contacts.info, contact_id, mutation)


def create_request_contact(backend: RegistryBackend, contact: RequestContact,
                           client_transaction_id) -> MutationResult | ErrorResponse:
    """Creates a request contact and reads it back, as the create reply does not hold it."""
    created = _gateways(backend).request_contacts.create(contact, client_transaction_id=client_transaction_id)
    if isinstance(created, ErrorResponse):
        return created
    return _read_back(backend, contact.id, created)


def _replaced(backend: RegistryBackend, contact_id: str, outcome, client_transaction_id) -> MutationResult | ErrorResponse:
    """The request contact read back, or as read when nothing changed, for its sponsor."""
    if isinstance(outcome, ErrorResponse):
        return outcome
    current = outcome.current
    if outcome.unchanged:
        refused = require_sponsor(backend, current.payload.clID, current, client_transaction_id, OBJECT)
        return refused or MutationResult(mutation=current, stored=current.payload)
    return _read_back(backend, contact_id, outcome.mutation)


def replace_request_contact(backend: RegistryBackend, wanted: RequestContact,
                            client_transaction_id) -> MutationResult | ErrorResponse:
    """A full update. A replacement that changes nothing sends no update (core §16.8 asks for a 200)."""
    outcome = _gateways(backend).request_contacts.replace(wanted, client_transaction_id=client_transaction_id)
    return _replaced(backend, wanted.id, outcome, client_transaction_id)


def patch_request_contact(
    backend: RegistryBackend, contact_id: str, wanted_from_current: Callable[[RequestContact], RequestContact],
    client_transaction_id,
) -> MutationResult | ErrorResponse:
    """A partial update: the request contact is read, `wanted_from_current` applies the patch, and the request
    contact is replaced with the result."""
    current = _gateways(backend).request_contacts.info(contact_id)
    if isinstance(current, ErrorResponse):
        return current
    outcome = _gateways(backend).request_contacts.replace(
        wanted_from_current(current.payload), current=current, client_transaction_id=client_transaction_id,
    )
    return _replaced(backend, contact_id, outcome, client_transaction_id)
