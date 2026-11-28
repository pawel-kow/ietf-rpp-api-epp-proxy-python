import importlib
from dataclasses import dataclass
from typing import Callable

from registry_adapter.rri.message_type import RriMessageType
from registry_adapter.rri.session.rri_client import RriClient


@dataclass(frozen=True)
class RriExtensionPart:
    """The RRI part of an extension: the gateways it gives a session, and the notifications of the registry it has message types
    for. The module of an extension (`registry_adapter.rri.extensions.<name>`) may have `gateways(client)` (an extension of message types only has none) and `MESSAGE_TYPES`, `ORGANISATION_MEMBERS`: what the extension
    adds to the organisation of a RegAcc, from its regacc INFO, and `CONTACT_MEMBERS`: what it adds to the contact commands (`read(InfoData)` gives
    its typed object of a contact INFO, `fields(object)` the fields of CREATE and UPDATE that state it)."""
    extension_id: str
    gateways: Callable[[RriClient], object] | None = None
    message_types: tuple[RriMessageType, ...] = ()
    organisation_members: Callable[[object], object] | None = None
    contact_members: object | None = None


def load_extension_parts(modules: dict[str, str], needing_gateways=frozenset()) -> list[RriExtensionPart]:
    """Imports the module of each registered extension that the RRI backend holds (by extension id). An extension that has
    objects, processes or handlers (`needing_gateways`) must have `gateways(client)`, and one without them is an error."""
    parts = []
    for extension_id, path in modules.items():
        try:
            module = importlib.import_module(path)
            parts.append(RriExtensionPart(extension_id=extension_id, gateways=getattr(module, "gateways", None),
                                          message_types=tuple(getattr(module, "MESSAGE_TYPES", ())),
                                          organisation_members=getattr(module, "ORGANISATION_MEMBERS", None),
                                          contact_members=getattr(module, "CONTACT_MEMBERS", None)))
            if extension_id in needing_gateways and parts[-1].gateways is None:
                raise ValueError(f"The RRI part {path!r} of the extension {extension_id} has no gateways(client), which an extension "
                                 f"with objects, processes or handlers needs")
        except (ImportError, AttributeError) as e:
            raise ValueError(f"The RRI part {path!r} of the extension {extension_id} cannot be loaded: {e}") from e
    return parts
