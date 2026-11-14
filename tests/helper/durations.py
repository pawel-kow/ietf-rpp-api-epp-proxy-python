"""ISO 8601 durations of the lifecycle facts (`PT2M`, `P1DT14H`), and the waits a run allows."""
import os
import re

DURATION = re.compile(r"P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?")
UNITS = (7 * 86400, 86400, 3600, 60, 1)

# The longest a case may wait, once, and the share of a period added to it, so a transition that a server runs a
# little late has passed. A run that may wait two days sets RPP_TEST_MAX_WAIT=P2DT12H.
MAX_WAIT_VARIABLE = "RPP_TEST_MAX_WAIT"
BUFFER_VARIABLE = "RPP_TEST_WAIT_BUFFER"
DEFAULT_MAX_WAIT = "PT10M"
DEFAULT_BUFFER_PERCENT = 10


def seconds(duration: str) -> int:
    """The seconds of an ISO 8601 duration of weeks, days, hours, minutes and seconds. Years and months, which
    have no fixed length, are refused."""
    match = DURATION.fullmatch(duration) if isinstance(duration, str) else None
    if match is None or duration in ("P", "PT") or duration.endswith("T"):
        raise ValueError(f"not an ISO 8601 duration of weeks, days, hours, minutes or seconds: {duration!r}")
    return sum(int(value) * unit for value, unit in zip(match.groups(), UNITS) if value)


def max_wait(environ=None) -> int:
    environ = os.environ if environ is None else environ
    return seconds(environ.get(MAX_WAIT_VARIABLE) or DEFAULT_MAX_WAIT)


def buffer_percent(environ=None) -> float:
    environ = os.environ if environ is None else environ
    value = environ.get(BUFFER_VARIABLE)
    percent = float(value) if value else DEFAULT_BUFFER_PERCENT
    if percent < 0:
        raise ValueError(f"{BUFFER_VARIABLE} is a percentage of 0 or more, not {value!r}")
    return percent
