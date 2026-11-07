from typing import Callable

from eppclient.epp_contacts import epp_contacts_Info, epp_contacts_Update
from eppclient.eppclient import EPPClient
from models import Contact, ContactInfoResponse, ContactUpdate, ErrorResponse, ResultCode
from .contact_mutation_result import ContactMutationResult
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


def _changes_nothing(update: ContactUpdate) -> bool:
    return update.add is None and update.remove is None and update.change is None


def _unchanged(epp_client: EPPClient, current: ContactInfoResponse, client_transaction_id) -> ContactMutationResult | ErrorResponse:
    """The answer to an update that changes nothing: the contact, for its sponsor."""
    refused = require_sponsor(epp_client, current.contact.clID, current, client_transaction_id, "contact")
    return refused or ContactMutationResult(mutation=current, contact=current.contact)


def patch_contact(
    epp_client: EPPClient,
    contact_id: str,
    update: ContactUpdate | None,
    update_from_current: Callable[[Contact], ContactUpdate],
    client_transaction_id,
) -> ContactMutationResult | ErrorResponse:
    """A partial update. Without an `update` the patch needs the current contact (#29): it is read, then
    `update_from_current` turns the patch into the difference. The read and the update are not atomic."""
    before = None
    if update is None:
        current = epp_contacts_Info(epp_client, contact_id)
        if isinstance(current, ErrorResponse):
            return current
        before = current.contact
        update = update_from_current(current.contact)
        if _changes_nothing(update):
            return _unchanged(epp_client, current, client_transaction_id)
    updated = epp_contacts_Update(epp_client, update, client_transaction_id=client_transaction_id)
    if isinstance(updated, ErrorResponse):
        return updated
    result = _read_back(epp_client, contact_id, updated)
    return (_lost_form(update, before, result, client_transaction_id) or result) if before else result


def replace_contact(
    epp_client: EPPClient,
    contact_id: str,
    update_from_current: Callable[[Contact], ContactUpdate],
    client_transaction_id,
) -> ContactMutationResult | ErrorResponse:
    """A full update: EPP has none, so it reads the contact and sends the difference. A replacement that changes
    nothing sends no update (core §16.8 asks for a 200)."""
    return patch_contact(epp_client, contact_id, None, update_from_current, client_transaction_id)
