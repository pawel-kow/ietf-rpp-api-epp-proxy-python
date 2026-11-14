"""The generic profiles of each protocol (src/settings/profiles), as the unit tests use them."""
import yaml

from core.capabilities.backend_profile import BackendProfile
from settings.load_settings import PROFILES


def generic_profile(protocol: str, lgrs=()) -> BackendProfile:
    with open(PROFILES / f"{protocol}.yaml", encoding="utf-8") as f:
        return BackendProfile.from_layers(yaml.safe_load(f), {"lgrs": list(lgrs)})


EPP_PROFILE = generic_profile("epp")
RRI_PROFILE = generic_profile("rri")
