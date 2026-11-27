from datetime import datetime, timezone


def utc_moment(value) -> datetime:
    """An RRI date and time (`XmlDateTime`) in UTC; one without an offset is taken as UTC."""
    moment = value.to_datetime()
    return moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment.astimezone(timezone.utc)


def utc_time(value) -> str:
    """An RRI date and time as an RPP one, in UTC with the fractional seconds the proxy always states."""
    return utc_moment(value).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
