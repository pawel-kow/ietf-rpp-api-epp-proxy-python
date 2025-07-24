import os
from typing import List, Optional
import yaml
from dataclasses import dataclass, field, fields

@dataclass
class Config:
    rpp_epp_host: str
    rpp_epp_port: Optional[int] = 700
    rpp_epp_use_tls: Optional[bool] = True
    rpp_epp_timeout: Optional[float] = 5.0

    rpp_epp_objects: List[str] = field(default_factory=lambda: [
        'urn:ietf:params:xml:ns:domain-1.0',
        'urn:ietf:params:xml:ns:contact-1.0',
        'urn:ietf:params:xml:ns:host-1.0',
    ])

    rpp_epp_extensions: Optional[List[str]] = None
    rpp_epp_connection_cache: Optional[bool] = False

    rpp_epp_ns_map: Optional[dict[str, str]] = field(default_factory=dict)



    def __init__(self):
        config_path = os.getenv("RPP_CONFIG_FILE", "./../config.yaml")
        with open(config_path) as f:
            data = yaml.safe_load(f)
        for f in fields(self):
            if f.name in data:
                setattr(self, f.name, data[f.name])


config = Config()
