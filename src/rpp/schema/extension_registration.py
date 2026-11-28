"""What the schema machinery takes from the extensions a deployment configured (`rpp_extensions`): their RPP extension
schema and the data model of their objects. These stay process-global and additive, as the machinery
already is (`EXTENSIONS`); what is per app (the presets, their profiles, the schemas and the validators) is built by `create_app`. Nothing is registered by an import: only `main` calls `register_all`, with the registry of the app it
builds. The per-app parts (paths, handlers, gateways) are not here."""
from registration import ExtensionRegistry
from rpp.schema.data_objects import register_data_objects
from rpp.schema.bundle_definitions import bundle_definitions
from rpp.schema.extensions import EXTENSIONS, _from_schema, register_extension


def _own_name(name: str) -> str:
    return name.split(".", 2)[2] if name.startswith("ext.") else name


def check_messages(extension) -> None:
    """What `rpp:messages` maps is a definition of the extension, with an identifier no base message type and no other
    extension's message type has: the identifiers share one namespace (the `type` of a Query)."""
    taken = {identifier: other.id for other in EXTENSIONS.values() if other.id != extension.id for identifier in other.messages}
    for identifier, name in extension.messages.items():
        if name not in extension.defs:
            raise ValueError(f"The extension {extension.id} maps the message type {identifier} to {name}, which it does not define")
        if f"{identifier}.read" in bundle_definitions():
            raise ValueError(f"The extension {extension.id} maps {identifier}, a message type of the base schema")
        if identifier in taken:
            raise ValueError(f"The extension {extension.id} maps {identifier}, which the extension {taken[identifier]} maps")


def check_names(schema: dict) -> None:
    """No definition of an extension has the name of a base definition, or of another extension's: the mappers name
    a definition without the extension (guidelines §8, D10), so a clash would validate with the wrong schema."""
    extension = _from_schema(schema)
    if extension.id in EXTENSIONS:
        return
    composed = set(extension.extends.values())
    taken = {_own_name(name): extension_id for extension_id, other in EXTENSIONS.items()
             for name in other.defs if name not in other.extends.values()}
    check_messages(extension)
    for name in extension.defs:
        if name in bundle_definitions():
            raise ValueError(f"The extension {extension.id} defines {name}, a definition of the base schema")
        if name in composed:
            continue
        if _own_name(name) in taken:
            raise ValueError(f"The extension {extension.id} defines {name}, which the extension "
                             f"{taken[_own_name(name)]} defines")


def register_all(registry: ExtensionRegistry) -> None:
    for extension in registry:
        check_names(extension.schema)
        register_extension(extension.schema, extension.processes)
        register_data_objects(extension.data_objects)
