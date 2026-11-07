import re
from datetime import datetime, timezone

from models import DomainRenew, DomainRenewProcess
from rpp_schema_validator import validate_schema
from .common import parse_rpp, period_duration, reject_set
from .rpp_models import RPPDomainRenewProcess


# RFC 3339 §5.6 date-time. The schema `format` is not enforced, so this is the whole check.
# Leap seconds (:60) are not accepted.
_DATE_TIME = re.compile(
    r"[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])[Tt]([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(\.[0-9]+)?([Zz]|[+-]([01][0-9]|2[0-3]):[0-5][0-9])"
)


def _utc_date(timestamp: str) -> str:
    """EPP holds the current expiry as a date only, so the time of day is not carried (json §8.1.7)."""
    if not _DATE_TIME.fullmatch(timestamp):
        raise ValueError(f"'{timestamp}' is not an RFC 3339 date-time")
    parsed = datetime.fromisoformat(timestamp.upper())
    return parsed.astimezone(timezone.utc).date().isoformat()


def rpp_to_model(name: str, rpp: dict, authorization: str | None) -> DomainRenew:
    """Converts a renew request. The date is the UTC date of `expiryDate`, None when the client gave none.
    EPP's renew has no authInfo, so the value of the RPP-Authorization header is refused."""
    validate_schema("renewProcess.create", rpp)
    process_rpp = parse_rpp(RPPDomainRenewProcess, rpp)
    reject_set(**{"RPP-Authorization": authorization})
    return DomainRenew(
        name=name,
        curExpDate=_utc_date(process_rpp.expiryDate) if process_rpp.expiryDate is not None else None,
        duration=period_duration(process_rpp.renewalPeriod),
    )


def model_to_rpp(process: DomainRenewProcess) -> dict:
    """EPP's renew response carries the new expiry date, but neither a period nor a process id."""
    process_rpp = RPPDomainRenewProcess(expiryDate=process.expiryDate).to_rpp()
    validate_schema("renewProcess.read", process_rpp)
    return process_rpp
