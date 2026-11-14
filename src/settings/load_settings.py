import os
from dataclasses import fields
from pathlib import Path

import yaml

from settings.discovery_settings import DiscoverySettings
from settings.epp_settings import EppSettings
from settings.rri_settings import RriSettings
from settings.settings import BACKENDS, Settings

# The generic profile of each protocol, which the profile of a server extends.
PROFILES = Path(__file__).resolve().parent / "profiles"


def _section(section, data: dict):
    return section(**{f.name: data[f.name] for f in fields(section) if f.name in data})


def _profile_layers(data: dict, backend: str) -> tuple[dict, ...]:
    """The layers of the backend profile: the generic profile `extends` names (the protocol's by default), then
    what `rpp_backend_profile` states besides."""
    specific = dict(data.get("rpp_backend_profile") or {})
    generic = specific.pop("extends", backend)
    if generic not in BACKENDS:
        raise ValueError(f"rpp_backend_profile extends one of {', '.join(BACKENDS)}, not {generic!r}")
    with open(PROFILES / f"{generic}.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f), specific


def load_settings(config_path: str | None = None) -> Settings:
    """Reads `config_path`, else the file `RPP_CONFIG_FILE` names, else config.yaml. An untracked <name>.local.yaml
    next to it replaces the top-level keys it has, for one machine's settings. Keys the proxy does not know are
    ignored."""
    config_path = config_path or os.getenv("RPP_CONFIG_FILE", "./config.yaml")
    with open(config_path) as f:
        data = yaml.safe_load(f)
    local_path = os.path.splitext(config_path)[0] + ".local.yaml"
    if os.path.exists(local_path):
        with open(local_path) as f:
            data.update(yaml.safe_load(f) or {})
    backend = data.get("rpp_backend", "epp")
    return Settings(
        epp=_section(EppSettings, data), discovery=_section(DiscoverySettings, data), rri=_section(RriSettings, data),
        backend=backend, profile_layers=_profile_layers(data, backend) if backend in BACKENDS else (),
    )
