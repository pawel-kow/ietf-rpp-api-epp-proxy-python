from dataclasses import replace
from typing import Callable

from eppclient.epp_domains import epp_domains_Info, epp_domains_Renew, epp_domains_Update
from eppclient.eppclient import EPPClient
from models import (
    Domain, DomainRenew, DomainRenewResponse, DomainReplacement, DomainUpdate, ErrorResponse, ResultCode, domain_difference,
)
from . import derived_update
from .domain_mutation_result import DomainMutationResult
from .replacement_steps import ReplacementSteps
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


DOMAIN_STEPS = ReplacementSteps(
    read=epp_domains_Info,
    object_of=lambda info: info.domain,
    difference=domain_difference.difference,
    changes_nothing=domain_difference.changes_nothing,
    update=epp_domains_Update,
)


def _replaced(epp_client: EPPClient, domain_name: str, outcome, client_transaction_id) -> DomainMutationResult | ErrorResponse:
    """The answer to a full update: the domain read back, or the domain as read when nothing changed, for its sponsor."""
    if isinstance(outcome, ErrorResponse):
        return outcome
    if outcome.unchanged:
        current = outcome.current
        refused = require_sponsor(epp_client, current.domain.clID, current, client_transaction_id, "domain")
        return refused or DomainMutationResult(mutation=current, domain=current.domain)
    return _read_back(epp_client, domain_name, outcome.mutation)


def patch_domain(
    epp_client: EPPClient,
    domain_name: str,
    update: DomainUpdate | None,
    wanted_from_current: Callable[[Domain], DomainReplacement],
    client_transaction_id,
) -> DomainMutationResult | ErrorResponse:
    """A partial update. Without an `update` the patch needs the current domain (#27): it is read,
    `wanted_from_current` applies the patch, and the domain is replaced with the result."""
    if update is not None:
        updated = epp_domains_Update(epp_client, update, client_transaction_id=client_transaction_id)
        if isinstance(updated, ErrorResponse):
            return updated
        return _read_back(epp_client, domain_name, updated)
    current = epp_domains_Info(epp_client, domain_name)
    if isinstance(current, ErrorResponse):
        return current
    outcome = derived_update.replace(
        DOMAIN_STEPS, epp_client, domain_name, wanted_from_current(current.domain), client_transaction_id, current,
    )
    return _replaced(epp_client, domain_name, outcome, client_transaction_id)


def replace_domain(epp_client: EPPClient, wanted: DomainReplacement, client_transaction_id) -> DomainMutationResult | ErrorResponse:
    """A full update. A replacement that changes nothing sends no update (core §16.8 asks for a 200)."""
    outcome = derived_update.replace(DOMAIN_STEPS, epp_client, wanted.name, wanted, client_transaction_id)
    return _replaced(epp_client, wanted.name, outcome, client_transaction_id)


def renew_domain(epp_client: EPPClient, renew: DomainRenew, client_transaction_id) -> DomainRenewResponse | ErrorResponse:
    """Renews a domain. EPP needs the current expiry date, so a client that gave none has it read (json §8.1.7).
    The read and the renew are not atomic, and without the client's date nothing guards against a double renewal."""
    if renew.curExpDate is None:
        current = epp_domains_Info(epp_client, renew.name)
        if isinstance(current, ErrorResponse):
            return current
        if not current.domain.exDate:
            return ErrorResponse(
                code=ResultCode.COMMAND_FAILED,
                msg="The registry reports no expiry date for the domain",
                server_transaction_id=current.server_transaction_id,
                client_transaction_id=client_transaction_id,
            )
        renew = replace(renew, curExpDate=current.domain.exDate[:10])
    return epp_domains_Renew(epp_client, renew, client_transaction_id=client_transaction_id)
