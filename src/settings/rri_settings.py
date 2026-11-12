from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RriSettings:
    """The connection to a DENIC RRI server. The names are the keys of config.yaml.

    `rpp_rri_lgr` is the one LGR name a client may give for the IDN repertoire of DENIC, none when no `lgr` is taken.
    """
    rpp_rri_host: Optional[str] = None
    rpp_rri_port: Optional[int] = 51131
    rpp_rri_use_tls: Optional[bool] = True
    rpp_rri_tls_insecure_skip_verify: Optional[bool] = False
    rpp_rri_timeout: Optional[float] = 5.0
    rpp_rri_lgr: Optional[str] = None
