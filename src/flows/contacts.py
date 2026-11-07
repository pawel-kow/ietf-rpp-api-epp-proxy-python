from typing import Callable

from eppclient.epp_contacts import epp_contacts_Info, epp_contacts_Update
from eppclient.eppclient import EPPClient
from models import Contact, ContactInfoResponse, ContactUpdate, ErrorResponse
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
    if update is None:
        current = epp_contacts_Info(epp_client, contact_id)
        if isinstance(current, ErrorResponse):
            return current
        update = update_from_current(current.contact)
        if _changes_nothing(update):
            return _unchanged(epp_client, current, client_transaction_id)
    updated = epp_contacts_Update(epp_client, update, client_transaction_id=client_transaction_id)
    if isinstance(updated, ErrorResponse):
        return updated
    return _read_back(epp_client, contact_id, updated)


def replace_contact(
    epp_client: EPPClient,
    contact_id: str,
    update_from_current: Callable[[Contact], ContactUpdate],
    client_transaction_id,
) -> ContactMutationResult | ErrorResponse:
    """A full update: EPP has none, so it reads the contact and sends the difference. A replacement that changes
    nothing sends no update (core §16.8 asks for a 200)."""
    return patch_contact(epp_client, contact_id, None, update_from_current, client_transaction_id)
