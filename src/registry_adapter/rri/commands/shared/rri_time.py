from datetime import timezone


def utc_time(value) -> str:
    """An RRI date and time (`XmlDateTime`) as an RPP one, in UTC with the fractional seconds the proxy always states."""
    return value.to_datetime().astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
