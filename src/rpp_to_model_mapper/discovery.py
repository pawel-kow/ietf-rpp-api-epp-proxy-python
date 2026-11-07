from urllib.parse import urlsplit

from models import Discovery
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


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _https_url(value) -> bool:
    if not _text(value):
        return False
    try:
        parts = urlsplit(value)
        return parts.scheme == "https" and bool(parts.hostname) and not any(c.isspace() for c in value)
    except ValueError:
        return False


def invalid_settings(settings) -> list[str]:
    """The names of the settings of the discovery document that are absent or of the wrong shape, never their values.

    `rpp_base_url` must be an absolute https URL (core §22), `rpp_tlds` a non-empty list of non-empty strings and the
    environment values non-empty strings.
    """
    tlds = getattr(settings, "rpp_tlds", None)
    checks = {
        "rpp_base_url": _https_url(getattr(settings, "rpp_base_url", None)),
        "rpp_tlds": isinstance(tlds, list) and bool(tlds) and all(_text(tld) for tld in tlds),
        "rpp_environment_name": _text(getattr(settings, "rpp_environment_name", None)),
        "rpp_environment_status": _text(getattr(settings, "rpp_environment_status", None)),
    }
    return [key for key, valid in checks.items() if not valid]
