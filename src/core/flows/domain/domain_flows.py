from dataclasses import replace
from typing import Callable

from core.model.domain.domain_renew import DomainRenew
from core.model.domain.domain_renew_response import DomainRenewResponse
from core.model.domain.domain_replacement import DomainReplacement
from core.model.domain.domain_restore_process import DomainRestoreProcess
from core.model.domain.domain_restore_response import DomainRestoreResponse
from core.model.domain.domains import Domain, DomainUpdate
from core.result.error_response import ErrorResponse
from core.result.result_code import ResultCode
from core.ports.registry_backend import RegistryBackend
from core.flows.domain.domain_mutation_result import DomainMutationResult
from core.flows.sponsor import require_sponsor


def _read_back(backend: RegistryBackend, domain_name: str, mutation) -> DomainMutationResult:
    """Reads the domain after a mutation the registry has already applied.

    A failed readback must not look like a failed mutation.
    """
    try:
        info = backend.domains.info(domain_name)
    except Exception:
        return DomainMutationResult(mutation=mutation)
    if isinstance(info, ErrorResponse):
        return DomainMutationResult(mutation=mutation)
    return DomainMutationResult(mutation=mutation, domain=info.domain)


def _replaced(backend: RegistryBackend, domain_name: str, outcome, client_transaction_id) -> DomainMutationResult | ErrorResponse:
    """The answer to a full update: the domain read back, or the domain as read when nothing changed, for its sponsor."""
    if isinstance(outcome, ErrorResponse):
        return outcome
    if outcome.unchanged:
        current = outcome.current
        refused = require_sponsor(backend, current.domain.clID, current, client_transaction_id, "domain")
        return refused or DomainMutationResult(mutation=current, domain=current.domain)
    return _read_back(backend, domain_name, outcome.mutation)


def patch_domain(
    backend: RegistryBackend,
    domain_name: str,
    update: DomainUpdate | None,
    wanted_from_current: Callable[[Domain], DomainReplacement],
    client_transaction_id,
) -> DomainMutationResult | ErrorResponse:
    """A partial update. Without an `update` the patch needs the current domain (#27): it is read,
    `wanted_from_current` applies the patch, and the domain is replaced with the result."""
    if update is not None:
        updated = backend.domains.update(update, client_transaction_id=client_transaction_id)
        if isinstance(updated, ErrorResponse):
            return updated
        return _read_back(backend, domain_name, updated)
    current = backend.domains.info(domain_name)
    if isinstance(current, ErrorResponse):
        return current
    outcome = backend.domains.replace(
        wanted_from_current(current.domain), current=current, client_transaction_id=client_transaction_id,
    )
    return _replaced(backend, domain_name, outcome, client_transaction_id)


def replace_domain(backend: RegistryBackend, wanted: DomainReplacement, client_transaction_id) -> DomainMutationResult | ErrorResponse:
    """A full update. A replacement that changes nothing sends no update (core §16.8 asks for a 200)."""
    outcome = backend.domains.replace(wanted, client_transaction_id=client_transaction_id)
    return _replaced(backend, wanted.name, outcome, client_transaction_id)


def renew_domain(backend: RegistryBackend, renew: DomainRenew, client_transaction_id) -> DomainRenewResponse | ErrorResponse:
    """Renews a domain. EPP needs the current expiry date, so a client that gave none has it read (json §8.1.7).
    The read and the renew are not atomic, and without the client's date nothing guards against a double renewal."""
    if renew.curExpDate is None:
        current = backend.domains.info(renew.name)
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
    return backend.domains.renew(renew, client_transaction_id=client_transaction_id)


def read_domain_restore(backend: RegistryBackend, domain_name: str, client_transaction_id) -> DomainRestoreResponse | ErrorResponse:
    """The restore of a domain, from its RGP statuses. EPP keeps no restore process and cannot tell a restored domain
    from one never deleted, so a domain without a restore under way has none (spec-issues.md, "Restore process")."""
    info = backend.domains.restore_info(domain_name, client_transaction_id=client_transaction_id)
    if isinstance(info, ErrorResponse):
        return info
    restore = DomainRestoreProcess(rgpStatus=info.domain.rgpStatus)
    if not restore.under_way():
        return ErrorResponse(
            code=ResultCode.OBJECT_DOES_NOT_EXIST,
            msg="The domain has no restore under way",
            server_transaction_id=info.server_transaction_id,
            client_transaction_id=info.client_transaction_id,
        )
    return DomainRestoreResponse(
        restore=restore,
        code=info.code,
        msg=info.msg,
        server_transaction_id=info.server_transaction_id,
        client_transaction_id=info.client_transaction_id,
    )

