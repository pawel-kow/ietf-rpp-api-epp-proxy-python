from core.capabilities.backend_profile import BackendProfile
from core.capabilities.backend_requirement import BackendRequirement
from core.capabilities.not_supported_by_backend import NotSupportedByBackend
from core.model.domain.domain_restore import DomainRestore
from core.model.domain.restore_report import RestoreReport
from rpp.dto.rpp_restore_report import RPPRestoreReport
from rpp.mapping.domain.domain_restore_process import parse_request
from rpp.mapping.shared.date_time import rfc3339

# RFC 3915 §4.2.5 requires every member of the report but `other`, and exactly two statements.
REQUIRED = ("preData", "postData", "deleteTime", "restoreTime", "restoreReason")

STATEMENTS = 2


def _report(report_rpp: RPPRestoreReport) -> RestoreReport:
    missing = [member for member in REQUIRED if getattr(report_rpp, member) is None]
    if missing:
        raise BackendRequirement(f"{{backend}} requires {', '.join(repr(member) for member in missing)} in the restore report")
    if len(report_rpp.statements or []) != STATEMENTS:
        raise BackendRequirement(f"{{backend}} requires exactly {STATEMENTS} statements in the restore report")
    return RestoreReport(
        preData=report_rpp.preData,
        postData=report_rpp.postData,
        deleteTime=rfc3339(report_rpp.deleteTime),
        restoreTime=rfc3339(report_rpp.restoreTime),
        restoreReason=report_rpp.restoreReason,
        statements=list(report_rpp.statements),
        other=report_rpp.other,
    )


def rpp_to_model(name: str, rpp: dict, *, profile: BackendProfile) -> DomainRestore:
    """Converts a restore report (json §8.1.14), which carries what RFC 3915 requires (json §6.2.10). A backend whose
    restore takes no report (`profile.domainName.processes.restore.report_supported`) refuses it."""
    if not profile.domainName.processes.restore.report_supported:
        raise NotSupportedByBackend("A restore report")
    process_rpp = parse_request("restoreProcess.update", rpp)
    return DomainRestore(name=name, report=_report(process_rpp.restoreReport))
