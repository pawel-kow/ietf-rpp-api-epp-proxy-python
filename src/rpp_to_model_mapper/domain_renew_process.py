from datetime import datetime, timezone

from models import DomainRenew, DomainRenewProcess
from rpp_schema_validator import validate_schema
from .common import parse_rpp, period_duration
from .rpp_models import RPPDomainRenewProcess


def _utc_date(timestamp: str) -> str:
    """EPP holds the current expiry as a date only, so the time of day is not carried (json §8.1.7)."""
    parsed = datetime.fromisoformat(timestamp)
    if parsed.tzinfo is None:
        raise ValueError(f"'{timestamp}' is not a date-time with an offset")
    return parsed.astimezone(timezone.utc).date().isoformat()


def rpp_to_model(name: str, rpp: dict) -> DomainRenew:
    """Converts a renew request. The date is the UTC date of `expiryDate`, None when the client gave none."""
    validate_schema("renewProcess.create", rpp)
    process_rpp = parse_rpp(RPPDomainRenewProcess, rpp)
    return DomainRenew(
        name=name,
        curExpDate=_utc_date(process_rpp.expiryDate) if process_rpp.expiryDate else None,
        duration=period_duration(process_rpp.renewalPeriod),
    )


def model_to_rpp(process: DomainRenewProcess) -> dict:
    """EPP's renew response carries the new expiry date, but neither a period nor a process id."""
    process_rpp = RPPDomainRenewProcess(expiryDate=process.expiryDate).to_rpp()
    validate_schema("renewProcess.read", process_rpp)
    return process_rpp
