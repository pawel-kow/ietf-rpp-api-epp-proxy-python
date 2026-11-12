from dataclasses import dataclass, field

from settings.discovery_settings import DiscoverySettings
from settings.epp_settings import EppSettings
from settings.rri_settings import RriSettings

BACKENDS = ("epp", "rri")


@dataclass(frozen=True)
class Settings:
    """The configuration, by the part of the proxy it is for. `main` loads it once and passes each section on.

    `backend` is the protocol the proxy speaks to the registry (`rpp_backend`): `epp` or `rri`.
    """
    epp: EppSettings
    discovery: DiscoverySettings
    rri: RriSettings = field(default_factory=RriSettings)
    backend: str = "epp"

    def __post_init__(self):
        if self.backend not in BACKENDS:
            raise ValueError(f"rpp_backend must be one of {', '.join(BACKENDS)}, not {self.backend!r}")
