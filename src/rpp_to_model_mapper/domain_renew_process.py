from datetime import datetime, timezone

from core.model.domain.domain_renew import DomainRenew
from core.model.domain.domain_renew_process import DomainRenewProcess
from rpp_schema_validator import validate_schema
from .date_time import rfc3339
from .common import parse_rpp, period_duration, reject_set
from .rpp_models import RPPDomainRenewProcess


def _utc_date(timestamp: str) -> str:
    """EPP holds the current expiry as a date only, so the time of day is not carried (json §8.1.7)."""
    parsed = datetime.fromisoformat(rfc3339(timestamp))
    return parsed.astimezone(timezone.utc).date().isoformat()


def rpp_to_model(name: str, rpp: dict, authorization: str | None) -> DomainRenew:
    """Converts a renew request. The date is the UTC date of `expiryDate`, None when the client gave none.
    EPP's renew has no authInfo, so the value of the RPP-Authorization header is refused."""
    validate_schema("renewProcess.create", rpp)
    process_rpp = parse_rpp(RPPDomainRenewProcess, rpp)
    cur_exp_date = _utc_date(process_rpp.expiryDate) if process_rpp.expiryDate is not None else None
    reject_set(**{"RPP-Authorization": authorization})
    return DomainRenew(
        name=name,
        curExpDate=cur_exp_date,
        duration=period_duration(process_rpp.renewalPeriod),
    )


def model_to_rpp(process: DomainRenewProcess) -> dict:
    """EPP's renew response carries the new expiry date, but neither a period nor a process id."""
    process_rpp = RPPDomainRenewProcess(expiryDate=process.expiryDate).to_rpp()
    validate_schema("renewProcess.read", process_rpp)
    return process_rpp
