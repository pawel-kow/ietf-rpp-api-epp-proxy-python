from datetime import datetime, timezone

FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def _utc(moment: datetime) -> datetime:
    """A moment in UTC; one without an offset is taken as UTC."""
    return moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment.astimezone(timezone.utc)


def utc_moment(value) -> datetime:
    """An RRI date and time (`XmlDateTime`) in UTC; one without an offset is taken as UTC."""
    return _utc(value.to_datetime())


def utc_time(value) -> str:
    """An RRI date and time as an RPP one, in UTC with the fractional seconds the proxy always states."""
    return utc_moment(value).strftime(FORMAT)


def utc_time_of_text(value: str) -> str:
    """The same for a date and time given as ISO 8601 text; one without an offset is taken as UTC."""
    return _utc(datetime.fromisoformat(value)).strftime(FORMAT)
