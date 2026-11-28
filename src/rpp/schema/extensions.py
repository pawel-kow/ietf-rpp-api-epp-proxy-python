"""The RPP extensions the proxy implements, which a deployment registers by its configuration (`rpp_extensions`,
`register_extension`): each has its schema file (copied from `.spec/` by copy_models.sh) in its own package. Which of them a
deployment holds is the `extensions` of its backend profile, and which it offers those of its presets."""
from rpp.schema.bundle_definitions import bundle_definitions
from rpp.schema.rpp_extension import RppExtension

_DEF = "#/$defs/"


def _name(ref: str) -> str:
    if not ref.startswith(_DEF):
        raise ValueError(f"An extension maps definitions of the bundle, not {ref!r}")
    return ref[len(_DEF):]


def _target(key: str) -> tuple[str, str | None]:
    """The definition an `rpp:extends` key names, and the `$id` of the extension that defines it (None for the bundle of RPP)."""
    uri, _, pointer = key.partition("#")
    return _name("#" + pointer), (uri or None)


def _from_schema(schema: dict) -> RppExtension:
    about = schema["rpp:extension"]
    if "rpp:constraints" in schema:
        raise ValueError(f"The Extension Schema of {about.get('id')} contains rpp:constraints, which only a Profile Schema has")
    targets = {key: _target(key) for key in schema["rpp:extends"]}
    for name, uri in targets.values():
        if uri is None and name not in bundle_definitions():
            raise ValueError(f"The extension {about.get('id')} extends {name}, which RPP does not define: a definition of another "
                             f"extension is named <$id of the owner>#/$defs/{name}")
    return RppExtension(
        id=about["id"], name=about["name"], version=about["version"], url=schema["$id"],
        extends={targets[key][0]: _name(ext) for key, ext in schema["rpp:extends"].items()},
        owners={name: uri for name, uri in targets.values() if uri},
        defs=schema["$defs"],
        objects=tuple(about.get("objects", ())),
    )


# The extensions registered in this process, by id. The generic code knows none until a configuration registers it.
EXTENSIONS: dict[str, RppExtension] = {}


def register_extension(schema: dict) -> RppExtension:
    """Adds the extension of a schema a configured extension registered. It is process-global and keyed by id, so
    registering it again is no change. Only `register()` of an extension the configuration names calls this."""
    extension = _from_schema(schema)
    if extension.id not in EXTENSIONS:
        EXTENSIONS[extension.id] = extension
    return EXTENSIONS[extension.id]


def added_members(schema_name: str, extensions) -> frozenset[str]:
    """The members the given extensions add to a base definition."""
    return frozenset(
        member
        for extension in extensions
        if schema_name in EXTENSIONS[extension].extends
        for member in EXTENSIONS[extension].defs[EXTENSIONS[extension].extends[schema_name]].get("properties", {})
    )


def check_known(extensions):
    """A backend profile that holds an extension the proxy does not implement is refused, so the app does not start."""
    unknown = sorted(set(extensions) - set(EXTENSIONS))
    if unknown:
        raise ValueError(f"backend profile: unknown RPP extension {', '.join(unknown)}")


def own_definitions(extensions=None) -> dict[str, str]:
    """The definitions of the objects and types the extensions define, by the name a mapper validates with
    (`planet.create`), to the name of the extension's definition: with a prefix (`ext.<name>.<definition>`),
    or the same name where an extension of new objects names them as the base definitions are (`planet.create`). The
    definitions an extension composes with a base one are not among them."""
    names = {}
    for extension in (EXTENSIONS[ext] for ext in extensions) if extensions is not None else EXTENSIONS.values():
        composed = set(extension.extends.values())
        for name in extension.defs:
            if name in composed:
                continue
            names[name.split(".", 2)[2] if name.startswith("ext.") else name] = name
    return names
