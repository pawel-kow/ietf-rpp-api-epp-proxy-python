from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class DiscoverySettings:
    """What the discovery document states, see core §11. All four are needed to answer it. The names are the keys of
    config.yaml."""
    rpp_base_url: Optional[str] = None
    rpp_tlds: Optional[List[str]] = None
    rpp_environment_name: Optional[str] = None
    rpp_environment_status: Optional[str] = None
