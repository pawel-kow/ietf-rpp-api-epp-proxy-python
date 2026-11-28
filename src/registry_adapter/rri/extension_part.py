import importlib
from dataclasses import dataclass
from typing import Callable

from registry_adapter.rri.session.rri_client import RriClient


@dataclass(frozen=True)
class RriExtensionPart:
    """The RRI part of an extension: the gateways it gives a session. The module of an extension
    (`registry_adapter.rri.extensions.<name>`) has `gateways(client)`."""
    extension_id: str
    gateways: Callable[[RriClient], object]


def load_extension_parts(modules: dict[str, str]) -> list[RriExtensionPart]:
    """Imports the module of each registered extension that the RRI backend holds (by extension id)."""
    parts = []
    for extension_id, path in modules.items():
        try:
            parts.append(RriExtensionPart(extension_id=extension_id, gateways=importlib.import_module(path).gateways))
        except (ImportError, AttributeError) as e:
            raise ValueError(f"The RRI part {path!r} of the extension {extension_id} cannot be loaded: {e}") from e
    return parts
