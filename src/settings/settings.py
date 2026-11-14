from dataclasses import dataclass, field

from settings.discovery_settings import DiscoverySettings
from settings.epp_settings import EppSettings
from settings.rri_settings import RriSettings

BACKENDS = ("epp", "rri")


@dataclass(frozen=True)
class Settings:
    """The configuration, by the part of the proxy it is for. `main` loads it once and passes each section on.

    `backend` is the protocol the proxy speaks to the registry (`rpp_backend`): `epp` or `rri`. `profile_layers`
    are the layers of its `BackendProfile`, the generic one of the protocol first, then the server's own
    (`rpp_backend_profile`); main merges them with `lgrs`.
    """
    epp: EppSettings
    discovery: DiscoverySettings
    rri: RriSettings = field(default_factory=RriSettings)
    backend: str = "epp"
    profile_layers: tuple[dict, ...] = ()

    def __post_init__(self):
        if self.backend not in BACKENDS:
            raise ValueError(f"rpp_backend must be one of {', '.join(BACKENDS)}, not {self.backend!r}")

    @property
    def lgrs(self) -> tuple[str, ...]:
        """The LGRs the backend offers for IDNs: those of the EPP IDN tables, or the one of DENIC's repertoire."""
        if self.backend == "rri":
            return (self.rri.rpp_rri_lgr,) if self.rri.rpp_rri_lgr else ()
        return tuple(sorted(self.epp.rpp_idn_lgr_tables or {}))
