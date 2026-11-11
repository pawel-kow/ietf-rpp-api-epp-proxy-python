from typing import Callable

from eppclient.epp_contacts import epp_contacts_Info, epp_contacts_Update
from eppclient.eppclient import EPPClient
from models import (
    Contact, ContactReplacement, ContactUpdate, ErrorResponse, ResultCode, contact_difference, contact_localization,
)
from . import derived_update, epp_contact_refusal
from .contact_mutation_result import ContactMutationResult
from .replacement_steps import ReplacementSteps
from .sponsor import require_sponsor


def _read_back(epp_client: EPPClient, contact_id: str, mutation) -> ContactMutationResult:
    """Reads the contact after a mutation the registry has already applied.

    A failed readback must not look like a failed mutation.
    """
    try:
        info = epp_contacts_Info(epp_client, contact_id)
    except Exception:
        return ContactMutationResult(mutation=mutation)
    if isinstance(info, ErrorResponse):
        return ContactMutationResult(mutation=mutation)
    return ContactMutationResult(mutation=mutation, contact=info.contact)


def _has_form(contact: Contact, form: str) -> bool:
    if form == "loc":
        return contact.localizedPostalInfo is not None
    return bool(contact.name or contact.organisationName or contact.address)


def _forms_the_registry_lost(update: ContactUpdate, before: Contact, after: Contact) -> list[str]:
    """A form that a `chg` adds is ignored by some registries, which still answer 1000. Only its presence is compared,
    the fields can come back normalised or cut."""
    forms = [change.form for change in update.change.postal_info] if update.change else []
    return [form for form in forms if not _has_form(before, form) and not _has_form(after, form)]


def _lost_form(update: ContactUpdate, before: Contact, result: ContactMutationResult, client_transaction_id) -> ErrorResponse | None:
    lost = _forms_the_registry_lost(update, before, result.contact) if result.contact else []
    if not lost:
        return None
    return ErrorResponse(
        code=ResultCode.COMMAND_FAILED,
        msg=f"The registry answered success but does not hold the '{lost[0]}' form of the contact",
        server_transaction_id=result.mutation.server_transaction_id,
        client_transaction_id=client_transaction_id,
    )


CONTACT_STEPS = ReplacementSteps(
    read=epp_contacts_Info,
    object_of=lambda info: info.contact,
    prepare=contact_localization.as_stored,
    refuse=epp_contact_refusal.refuse,
    difference=contact_difference.difference,
    changes_nothing=contact_difference.changes_nothing,
    update=epp_contacts_Update,
)


def _replaced(epp_client: EPPClient, contact_id: str, outcome, client_transaction_id) -> ContactMutationResult | ErrorResponse:
    """The answer to a full update: the contact read back, or the contact as read when nothing changed, for its
    sponsor. A form the update added and the registry still lacks is an error."""
    if isinstance(outcome, ErrorResponse):
        return outcome
    current = outcome.current
    if outcome.unchanged:
        refused = require_sponsor(epp_client, current.contact.clID, current, client_transaction_id, "contact")
        return refused or ContactMutationResult(mutation=current, contact=current.contact)
    result = _read_back(epp_client, contact_id, outcome.mutation)
    return _lost_form(outcome.update, current.contact, result, client_transaction_id) or result


def patch_contact(
    epp_client: EPPClient,
    contact_id: str,
    update: ContactUpdate | None,
    wanted_from_current: Callable[[Contact], ContactReplacement],
    client_transaction_id,
) -> ContactMutationResult | ErrorResponse:
    """A partial update. Without an `update` the patch needs the current contact (#29): it is read,
    `wanted_from_current` applies the patch, and the contact is replaced with the result."""
    if update is not None:
        updated = epp_contacts_Update(epp_client, update, client_transaction_id=client_transaction_id)
        if isinstance(updated, ErrorResponse):
            return updated
        return _read_back(epp_client, contact_id, updated)
    current = epp_contacts_Info(epp_client, contact_id)
    if isinstance(current, ErrorResponse):
        return current
    outcome = derived_update.replace(
        CONTACT_STEPS, epp_client, contact_id, wanted_from_current(current.contact), client_transaction_id, current,
    )
    return _replaced(epp_client, contact_id, outcome, client_transaction_id)


def replace_contact(epp_client: EPPClient, wanted: ContactReplacement, client_transaction_id) -> ContactMutationResult | ErrorResponse:
    """A full update. A replacement that changes nothing sends no update (core §16.8 asks for a 200)."""
    outcome = derived_update.replace(CONTACT_STEPS, epp_client, wanted.id, wanted, client_transaction_id)
    return _replaced(epp_client, wanted.id, outcome, client_transaction_id)
