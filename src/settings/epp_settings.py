from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class EppSettings:
    """The connection to the EPP server and how the proxy speaks EPP. The names are the keys of config.yaml."""
    rpp_epp_host: Optional[str] = None
    rpp_epp_port: Optional[int] = 700
    rpp_epp_use_tls: Optional[bool] = True
    rpp_epp_tls_insecure_skip_verify: Optional[bool] = False
    rpp_epp_timeout: Optional[float] = 5.0

    rpp_epp_objects: List[str] = field(default_factory=lambda: [
        'urn:ietf:params:xml:ns:domain-1.0',
        'urn:ietf:params:xml:ns:contact-1.0',
        'urn:ietf:params:xml:ns:host-1.0',
    ])

    rpp_epp_extensions: Optional[List[str]] = None
    rpp_epp_connection_cache: Optional[bool] = False

    rpp_epp_ns_map: Optional[dict[str, str]] = field(default_factory=dict)

    # LGR name (json §6.4) to the IDN table id of the EPP IDN extension, one to one.
    rpp_idn_lgr_tables: Optional[dict[str, str]] = None
