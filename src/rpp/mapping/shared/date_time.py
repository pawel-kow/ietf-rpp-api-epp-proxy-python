import re

# RFC 3339 §5.6 date-time. The schema `format` is not enforced, so this is the whole check.
# Leap seconds (:60) are not accepted.
_DATE_TIME = re.compile(
    r"[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])[Tt]([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(\.[0-9]+)?([Zz]|[+-]([01][0-9]|2[0-3]):[0-5][0-9])"
)


def rfc3339(timestamp: str) -> str:
    """The date-time with `T` and `Z` in upper case. Anything but an RFC 3339 date-time is a ValueError."""
    if not _DATE_TIME.fullmatch(timestamp):
        raise ValueError(f"'{timestamp}' is not an RFC 3339 date-time")
    return timestamp.upper()
