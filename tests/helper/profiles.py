"""The generic profiles of each protocol (src/settings/profiles), as the unit tests use them. The RRI profile is the one of a
server that registers the rri extension (config/backends/rri.yaml), which adds its objects, extension, preset and leaves."""
import yaml

from core.capabilities.backend_profile import BackendProfile
from registry_adapter.rri.extension_part import load_extension_parts as load_rri_parts
from registration import ExtensionRegistry, load_extensions, with_extensions
from rpp.schema.extension_registration import register_all
from settings.load_settings import PROFILES

RRI_EXTENSION = "extensions.rri"


def registry_of(*modules: str) -> ExtensionRegistry:
    """The extensions of these modules, registered as `main` registers those a configuration names."""
    registry = load_extensions(modules)
    register_all(registry)
    return registry


def generic_profile(protocol: str, lgrs=(), registry: ExtensionRegistry | None = None) -> BackendProfile:
    """The generic profile of a protocol, with what the extensions of `registry` add to it."""
    with open(PROFILES / f"{protocol}.yaml", encoding="utf-8") as f:
        layers = [yaml.safe_load(f)]
    registry = registry or ExtensionRegistry()
    return BackendProfile.from_layers(*with_extensions(layers, registry), {"lgrs": list(lgrs)},
                                      extra_leaves=registry.profile_leaves())


RRI_REGISTRY = registry_of(RRI_EXTENSION)
EPP_PROFILE = generic_profile("epp")
RRI_PROFILE = generic_profile("rri", registry=RRI_REGISTRY)

RRI_PARTS = load_rri_parts(RRI_REGISTRY.backend_parts("rri"))
