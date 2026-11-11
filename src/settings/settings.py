from dataclasses import dataclass

from settings.discovery_settings import DiscoverySettings
from settings.epp_settings import EppSettings


@dataclass(frozen=True)
class Settings:
    """The configuration, by the part of the proxy it is for. `main` loads it once and passes each section on."""
    epp: EppSettings
    discovery: DiscoverySettings
