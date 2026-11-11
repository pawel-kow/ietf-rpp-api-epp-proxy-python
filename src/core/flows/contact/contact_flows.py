from typing import Callable

from core.model.contact.contact_replacement import ContactReplacement
from core.model.contact.contact_update import ContactUpdate
from core.model.contact.contacts import Contact
from core.result.error_response import ErrorResponse
from core.result.result_code import ResultCode
from core.ports.registry_backend import RegistryBackend
from core.flows.mutation_result import MutationResult
from core.flows.read_back import read_back
from core.flows.sponsor import require_sponsor


def _read_back(backend: RegistryBackend, contact_id: str, mutation) -> MutationResult:
    return read_back(backend.contacts.info, contact_id, mutation)


def create_contact(backend: RegistryBackend, contact: Contact, client_transaction_id) -> MutationResult | ErrorResponse:
    """Creates a contact and reads it back, as the create reply does not hold the contact."""
    created = backend.contacts.create(contact, client_transaction_id=client_transaction_id)
    if isinstance(created, ErrorResponse):
        return created
    return _read_back(backend, created.payload.id, created)


def _has_form(contact: Contact, form: str) -> bool:
    if form == "loc":
        return contact.localizedPostalInfo is not None
    return bool(contact.name or contact.organisationName or contact.address)


def _forms_the_registry_lost(update: ContactUpdate, before: Contact, after: Contact) -> list[str]:
    """A form that a `chg` adds is ignored by some registries, which still answer 1000. Only its presence is compared,
    the fields can come back normalised or cut."""
    forms = [change.form for change in update.change.postal_info] if update.change else []
    return [form for form in forms if not _has_form(before, form) and not _has_form(after, form)]


def _lost_form(update: ContactUpdate, before: Contact, result: MutationResult, client_transaction_id) -> ErrorResponse | None:
    lost = _forms_the_registry_lost(update, before, result.stored) if result.stored else []
    if not lost:
        return None
    return ErrorResponse(
        code=ResultCode.COMMAND_FAILED,
        msg=f"The registry answered success but does not hold the '{lost[0]}' form of the contact",
        server_transaction_id=result.mutation.server_transaction_id,
        client_transaction_id=client_transaction_id,
    )


def _replaced(backend: RegistryBackend, contact_id: str, outcome, client_transaction_id) -> MutationResult | ErrorResponse:
    """The answer to a full update: the contact read back, or the contact as read when nothing changed, for its
    sponsor. A form the update added and the registry still lacks is an error."""
    if isinstance(outcome, ErrorResponse):
        return outcome
    current = outcome.current
    if outcome.unchanged:
        refused = require_sponsor(backend, current.payload.clID, current, client_transaction_id, "contact")
        return refused or MutationResult(mutation=current, stored=current.payload)
    result = _read_back(backend, contact_id, outcome.mutation)
    return _lost_form(outcome.update, current.payload, result, client_transaction_id) or result


def patch_contact(
    backend: RegistryBackend,
    contact_id: str,
    update: ContactUpdate | None,
    wanted_from_current: Callable[[Contact], ContactReplacement],
    client_transaction_id,
) -> MutationResult | ErrorResponse:
    """A partial update. Without an `update` the patch needs the current contact (#29): it is read,
    `wanted_from_current` applies the patch, and the contact is replaced with the result."""
    if update is not None:
        updated = backend.contacts.update(update, client_transaction_id=client_transaction_id)
        if isinstance(updated, ErrorResponse):
            return updated
        return _read_back(backend, contact_id, updated)
    current = backend.contacts.info(contact_id)
    if isinstance(current, ErrorResponse):
        return current
    outcome = backend.contacts.replace(
        wanted_from_current(current.payload), current=current, client_transaction_id=client_transaction_id,
    )
    return _replaced(backend, contact_id, outcome, client_transaction_id)


def replace_contact(backend: RegistryBackend, wanted: ContactReplacement, client_transaction_id) -> MutationResult | ErrorResponse:
    """A full update. A replacement that changes nothing sends no update (core §16.8 asks for a 200)."""
    outcome = backend.contacts.replace(wanted, client_transaction_id=client_transaction_id)
    return _replaced(backend, wanted.id, outcome, client_transaction_id)
