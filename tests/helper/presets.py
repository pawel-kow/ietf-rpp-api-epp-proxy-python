"""The presets a generic profile of each protocol offers (src/settings/profiles), as the unit tests use them."""
from core.capabilities.backend_profile import BackendProfile
from rpp.schema.definitions import Definitions
from rpp.schema.extensions import EXTENSIONS
from rpp.schema.offered_presets import OfferedPresets
from tests.helper.profiles import EPP_PROFILE, RRI_PROFILE, RRI_REGISTRY


def offered(profile: BackendProfile, registry=None) -> OfferedPresets:
    return OfferedPresets.build(Definitions.load(registry, EXTENSIONS), profile.presets, profile.default_preset,
                                profile.bound_profiles, profile.extensions)


EPP_PRESETS = offered(EPP_PROFILE)
RRI_PRESETS = offered(RRI_PROFILE, RRI_REGISTRY)

BASE = "urn:ietf:params:rpp:preset:base"
EPP = "urn:ietf:params:rpp:preset:epp-compatible"
RRI = "de.denic.rpp.preset.rri"
EPP_COMPATIBILITY = "urn:ietf:params:rpp:profile:epp-compatibility"
