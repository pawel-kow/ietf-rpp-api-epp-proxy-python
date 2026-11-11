from models import DomainRestore, DomainRestoreProcess
from models.domain_restore_process import PENDING_DELETE, PENDING_RESTORE
from rpp_schema_validator import validate_schema
from .common import parse_rpp
from .not_supported_by_backend import NotSupportedByBackend
from .rpp_models import RPPRestoreProcess

def parse_request(schema: str, rpp: dict) -> RPPRestoreProcess:
    """A restore process sent by the client, which has no read-only members (json §6.3.5)."""
    validate_schema(schema, rpp)
    process_rpp = parse_rpp(RPPRestoreProcess, rpp)
    if process_rpp.restoreStatus is not None:
        raise ValueError("'restoreStatus' is read-only")
    return process_rpp


def rpp_to_model(name: str, rpp: dict) -> DomainRestore:
    """Converts a restore request (json §8.1.13). RFC 3915 restores in two steps, a request and then a report,
    so a report inside the request has no place in EPP."""
    process_rpp = parse_request("restoreProcess.create", rpp)
    if process_rpp.restoreReport is not None:
        raise NotSupportedByBackend("A 'restoreReport' in a restore request")
    return DomainRestore(name=name)


def restore_status(rgp_status: list[str]) -> str | None:
    """The `restoreStatus` of a domain's RGP statuses (RFC 3915 §3.2), None when none says a restore is under way."""
    if PENDING_RESTORE in rgp_status:
        return "pendingRestore"
    if PENDING_DELETE in rgp_status:
        return "rgpPendingDelete"
    return None


def model_to_rpp(process: DomainRestoreProcess) -> dict:
    """EPP has no process id and no dates, so the representation is the status alone. A domain without an RGP
    status of a restore under way is restored."""
    process_rpp = RPPRestoreProcess(restoreStatus=restore_status(process.rgpStatus) or "restored").to_rpp()
    validate_schema("restoreProcess.read", process_rpp)
    return process_rpp
