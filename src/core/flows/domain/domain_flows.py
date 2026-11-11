from dataclasses import replace
from typing import Callable

from core.flows.mutation_result import MutationResult
from core.flows.read_back import read_back
from core.flows.sponsor import require_sponsor
from core.model.domain.domain_renew import DomainRenew
from core.model.domain.domain_renew_process import DomainRenewProcess
from core.model.domain.domain_replacement import DomainReplacement
from core.model.domain.domain_restore_process import DomainRestoreProcess
from core.model.domain.domains import Domain, DomainUpdate
from core.ports.registry_backend import RegistryBackend
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from core.result.result_code import ResultCode


def _read_back(backend: RegistryBackend, domain_name: str, mutation) -> MutationResult:
    return read_back(backend.domains.info, domain_name, mutation)


def create_domain(backend: RegistryBackend, domain: Domain, client_transaction_id) -> MutationResult | ErrorResponse:
    """Creates a domain and reads it back, as the create reply does not hold the domain."""
    created = backend.domains.create(domain, client_transaction_id=client_transaction_id)
    if isinstance(created, ErrorResponse):
        return created
    return _read_back(backend, created.payload.name, created)


def _replaced(backend: RegistryBackend, domain_name: str, outcome, client_transaction_id) -> MutationResult | ErrorResponse:
    """The answer to a full update: the domain read back, or the domain as read when nothing changed, for its sponsor."""
    if isinstance(outcome, ErrorResponse):
        return outcome
    if outcome.unchanged:
        current = outcome.current
        refused = require_sponsor(backend, current.payload.clID, current, client_transaction_id, "domain")
        return refused or MutationResult(mutation=current, stored=current.payload)
    return _read_back(backend, domain_name, outcome.mutation)


def patch_domain(
    backend: RegistryBackend,
    domain_name: str,
    update: DomainUpdate | None,
    wanted_from_current: Callable[[Domain], DomainReplacement],
    client_transaction_id,
) -> MutationResult | ErrorResponse:
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
        wanted_from_current(current.payload), current=current, client_transaction_id=client_transaction_id,
    )
    return _replaced(backend, domain_name, outcome, client_transaction_id)


def replace_domain(backend: RegistryBackend, wanted: DomainReplacement, client_transaction_id) -> MutationResult | ErrorResponse:
    """A full update. A replacement that changes nothing sends no update (core §16.8 asks for a 200)."""
    outcome = backend.domains.replace(wanted, client_transaction_id=client_transaction_id)
    return _replaced(backend, wanted.name, outcome, client_transaction_id)


def renew_domain(backend: RegistryBackend, renew: DomainRenew, client_transaction_id) -> OperationResponse[DomainRenewProcess] | ErrorResponse:
    """Renews a domain. EPP needs the current expiry date, so a client that gave none has it read (json §8.1.7).
    The read and the renew are not atomic, and without the client's date nothing guards against a double renewal."""
    if renew.curExpDate is None:
        current = backend.domains.info(renew.name)
        if isinstance(current, ErrorResponse):
            return current
        if not current.payload.exDate:
            return ErrorResponse(
                code=ResultCode.COMMAND_FAILED,
                msg="The registry reports no expiry date for the domain",
                server_transaction_id=current.server_transaction_id,
                client_transaction_id=client_transaction_id,
            )
        renew = replace(renew, curExpDate=current.payload.exDate[:10])
    return backend.domains.renew(renew, client_transaction_id=client_transaction_id)


def read_domain_restore(backend: RegistryBackend, domain_name: str, client_transaction_id) -> OperationResponse[DomainRestoreProcess] | ErrorResponse:
    """The restore of a domain, from its RGP statuses. EPP keeps no restore process and cannot tell a restored domain
    from one never deleted, so a domain without a restore under way has none (spec-issues.md, "Restore process")."""
    info = backend.domains.restore_info(domain_name, client_transaction_id=client_transaction_id)
    if isinstance(info, ErrorResponse):
        return info
    restore = DomainRestoreProcess(rgpStatus=info.payload.rgpStatus)
    if not restore.under_way():
        return ErrorResponse(
            code=ResultCode.OBJECT_DOES_NOT_EXIST,
            msg="The domain has no restore under way",
            server_transaction_id=info.server_transaction_id,
            client_transaction_id=info.client_transaction_id,
        )
    return OperationResponse(
        code=info.code, msg=info.msg, server_transaction_id=info.server_transaction_id,
        client_transaction_id=info.client_transaction_id, payload=restore,
    )

