"""What `main` and the tests of the test environments build the backend profile from: the extensions the settings name,
registered, and the profile with what they add. A module of its own, so that building a profile composes no app."""
import importlib
import importlib.util

from core.capabilities.backend_profile import BackendProfile
from registration import ExtensionRegistry, load_extensions, with_extensions
from rpp.schema.extension_registration import register_all
from settings.settings import Settings


def held_parts(backend: str) -> dict[str, str]:
    """The extensions the backend holds, the module of its part of each by extension id (`PARTS` of
    `registry_adapter.<backend>.extensions`). A backend without that package (EPP) holds none."""
    package = f"registry_adapter.{backend}.extensions"
    if importlib.util.find_spec(package) is None:
        return {}
    return importlib.import_module(package).PARTS


def backend_parts(backend: str, registry: ExtensionRegistry) -> dict[str, str]:
    """The parts of the backend for the registered extensions only, by extension id."""
    held = held_parts(backend)
    return {extension_id: held[extension_id] for extension_id in registry.ids() if extension_id in held}


def load_registry(settings: Settings) -> ExtensionRegistry:
    """The extensions the settings name (`rpp_extensions`), registered. The schema and the data model of each become
    the process's (`register_all`), so that a profile of them can be built; nothing is registered without this call, and
    an extension that the backend of the settings cannot hold stops the app."""
    registry = load_extensions(settings.extensions)
    for extension in registry:
        if extension.id not in held_parts(settings.backend):
            raise ValueError(f"rpp_extensions: the extension {extension.id} has no part in the {settings.backend} backend")
    register_all(registry)
    return registry


def backend_profile(settings: Settings, registry: ExtensionRegistry) -> BackendProfile:
    """The generic profile of the protocol, what the registered extensions add to it, the server's own over them, and
    the LGRs of the config."""
    return BackendProfile.from_layers(
        *with_extensions(settings.profile_layers, registry), {"lgrs": list(settings.lgrs)},
        extra_leaves=registry.profile_leaves())
