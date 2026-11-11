import re
from urllib.parse import urlsplit

from core.model.shared.discovery import Discovery
from rpp_schema_validator import validate_schema
from .rpp_models import RPPDiscovery, RPPDiscoveryEnvironment, RPPDiscoveryVersion


def model_to_rpp(discovery: Discovery) -> dict:
    rpp = RPPDiscovery(
        versions=[RPPDiscoveryVersion(version=discovery.version, base_url=discovery.base_url)],
        environment=RPPDiscoveryEnvironment(name=discovery.environment_name, status=discovery.environment_status),
        tlds=discovery.tlds,
        profiles=discovery.profiles,
        objects=discovery.objects,
        datetime=discovery.datetime,
    ).to_rpp()
    validate_schema("discovery.read", rpp)
    return rpp


# The characters a URI may have (RFC 3986), without `?` and `#`, which the base URL may not have anyway.
_URI_CHARACTERS = re.compile(r"[A-Za-z0-9\-._~:/\[\]@!$&'()*+,;=%]+")


def _text(value) -> bool:
    """A non-empty string with no control characters and no padding."""
    return isinstance(value, str) and bool(value) and value == value.strip() and not any(ord(c) < 32 or ord(c) == 127 for c in value)


def _tld(value) -> bool:
    return _text(value) and not any(c.isspace() for c in value)


def _https_url(value) -> bool:
    """An absolute https URL with a host, usable as a prefix: no userinfo, query or fragment, and no malformed escape."""
    if not _text(value) or not _URI_CHARACTERS.fullmatch(value) or any(c.isspace() or c == "\\" for c in value) or re.search(r"%(?![0-9A-Fa-f]{2})", value):
        return False
    try:
        parts = urlsplit(value)
        parts.port  # raises ValueError for a port that is not a number or out of range
        return (
            parts.scheme == "https" and bool(parts.hostname) and "@" not in parts.netloc
            and "?" not in value and "#" not in value
        )
    except ValueError:
        return False


def invalid_settings(settings) -> list[str]:
    """The names of the settings of the discovery document that are absent or of the wrong shape, never their values.

    `rpp_base_url` must be an absolute https URL (core §22), `rpp_tlds` a non-empty list of strings without whitespace and the
    environment values non-empty strings, none of them padded or with control characters.
    """
    tlds = getattr(settings, "rpp_tlds", None)
    checks = {
        "rpp_base_url": _https_url(getattr(settings, "rpp_base_url", None)),
        "rpp_tlds": isinstance(tlds, list) and bool(tlds) and all(_tld(tld) for tld in tlds),
        "rpp_environment_name": _text(getattr(settings, "rpp_environment_name", None)),
        "rpp_environment_status": _text(getattr(settings, "rpp_environment_status", None)),
    }
    return [key for key, valid in checks.items() if not valid]
