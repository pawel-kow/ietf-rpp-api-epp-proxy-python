from typing import Callable

from eppclient.epp_domains import epp_domains_Info, epp_domains_Update
from eppclient.eppclient import EPPClient
from models import Domain, DomainInfoResponse, DomainUpdate, ErrorResponse
from .domain_mutation_result import DomainMutationResult
from .sponsor import require_sponsor


def _read_back(epp_client: EPPClient, domain_name: str, mutation) -> DomainMutationResult:
    """Reads the domain after a mutation the registry has already applied.

    A failed readback must not look like a failed mutation.
    """
    try:
        info = epp_domains_Info(epp_client, domain_name)
    except Exception:
        return DomainMutationResult(mutation=mutation)
    if isinstance(info, ErrorResponse):
        return DomainMutationResult(mutation=mutation)
    return DomainMutationResult(mutation=mutation, domain=info.domain)


def _changes_nothing(update: DomainUpdate) -> bool:
    return update.add is None and update.remove is None and update.change is None


def _unchanged(epp_client: EPPClient, current: DomainInfoResponse, client_transaction_id) -> DomainMutationResult | ErrorResponse:
    """The answer to an update that changes nothing: the domain, for its sponsor."""
    refused = require_sponsor(epp_client, current.domain.clID, current, client_transaction_id, "domain")
    return refused or DomainMutationResult(mutation=current, domain=current.domain)


def patch_domain(
    epp_client: EPPClient,
    domain_name: str,
    update: DomainUpdate | None,
    update_from_current: Callable[[Domain], DomainUpdate],
    client_transaction_id,
) -> DomainMutationResult | ErrorResponse:
    """A partial update. Without an `update` the patch needs the current domain (#27): it is read, then
    `update_from_current` turns the patch into the difference. The read and the update are not atomic."""
    if update is None:
        current = epp_domains_Info(epp_client, domain_name)
        if isinstance(current, ErrorResponse):
            return current
        update = update_from_current(current.domain)
        if _changes_nothing(update):
            return _unchanged(epp_client, current, client_transaction_id)
    updated = epp_domains_Update(epp_client, update, client_transaction_id=client_transaction_id)
    if isinstance(updated, ErrorResponse):
        return updated
    return _read_back(epp_client, domain_name, updated)


def replace_domain(
    epp_client: EPPClient,
    domain_name: str,
    update_from_current: Callable[[Domain], DomainUpdate],
    client_transaction_id,
) -> DomainMutationResult | ErrorResponse:
    """A full update: EPP has none, so it reads the domain and sends the difference. A replacement that changes
    nothing sends no update (core §16.8 asks for a 200)."""
    return patch_domain(epp_client, domain_name, None, update_from_current, client_transaction_id)
