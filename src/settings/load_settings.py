import os
from dataclasses import fields

import yaml

from settings.discovery_settings import DiscoverySettings
from settings.epp_settings import EppSettings
from settings.rri_settings import RriSettings
from settings.settings import Settings


def _section(section, data: dict):
    return section(**{f.name: data[f.name] for f in fields(section) if f.name in data})


def load_settings() -> Settings:
    """Reads config.yaml, or the file `RPP_CONFIG_FILE` names. An untracked <name>.local.yaml next to it replaces the
    top-level keys it has, for one machine's settings. Keys the proxy does not know are ignored."""
    config_path = os.getenv("RPP_CONFIG_FILE", "./config.yaml")
    with open(config_path) as f:
        data = yaml.safe_load(f)
    local_path = os.path.splitext(config_path)[0] + ".local.yaml"
    if os.path.exists(local_path):
        with open(local_path) as f:
            data.update(yaml.safe_load(f) or {})
    return Settings(
        epp=_section(EppSettings, data), discovery=_section(DiscoverySettings, data), rri=_section(RriSettings, data),
        backend=data.get("rpp_backend", "epp"),
    )
