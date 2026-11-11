from models import DomainRestore, RestoreReport
from .date_time import rfc3339
from .domain_restore_process import parse_request
from .rpp_models import RPPRestoreReport

# RFC 3915 §4.2.5 requires every member of the report but `other`, and exactly two statements.
REQUIRED = ("preData", "postData", "deleteTime", "restoreTime", "restoreReason")
STATEMENTS = 2


def _report(report_rpp: RPPRestoreReport) -> RestoreReport:
    missing = [member for member in REQUIRED if getattr(report_rpp, member) is None]
    if missing:
        raise ValueError(f"EPP requires {', '.join(repr(member) for member in missing)} in the restore report")
    if len(report_rpp.statements or []) != STATEMENTS:
        raise ValueError(f"EPP requires exactly {STATEMENTS} statements in the restore report")
    return RestoreReport(
        preData=report_rpp.preData,
        postData=report_rpp.postData,
        deleteTime=rfc3339(report_rpp.deleteTime),
        restoreTime=rfc3339(report_rpp.restoreTime),
        restoreReason=report_rpp.restoreReason,
        statements=list(report_rpp.statements),
        other=report_rpp.other,
    )


def rpp_to_model(name: str, rpp: dict) -> DomainRestore:
    """Converts a restore report (json §8.1.14), which carries what RFC 3915 requires (json §6.2.10)."""
    process_rpp = parse_request("restoreProcess.update", rpp)
    return DomainRestore(name=name, report=_report(process_rpp.restoreReport))
