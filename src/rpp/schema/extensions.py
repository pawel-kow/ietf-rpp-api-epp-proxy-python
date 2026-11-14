"""The RPP extensions the proxy implements, one schema file each in `schemas/extensions/` (copied from `.spec/` by
copy_models.sh). Which of them a deployment offers is the `extensions` of its backend profile."""
import json
from pathlib import Path

from rpp.schema.rpp_extension import RppExtension

FOLDER = Path(__file__).parent / "schemas" / "extensions"

_DEF = "#/$defs/"


def _name(ref: str) -> str:
    if not ref.startswith(_DEF):
        raise ValueError(f"An extension maps definitions of the bundle, not {ref!r}")
    return ref[len(_DEF):]


def _load(path: Path) -> RppExtension:
    with open(path, encoding="utf-8") as f:
        schema = json.load(f)
    about = schema["rpp:extension"]
    return RppExtension(
        id=about["id"], name=about["name"], version=about["version"], url=schema["$id"],
        extends={_name(base): _name(ext) for base, ext in schema["rpp:extends"].items()},
        defs=schema["$defs"],
    )


EXTENSIONS: dict[str, RppExtension] = {
    extension.id: extension for extension in map(_load, sorted(FOLDER.glob("*.json")))
}


def added_members(schema_name: str, extensions) -> frozenset[str]:
    """The members the given extensions add to a base definition."""
    return frozenset(
        member
        for extension in extensions
        if schema_name in EXTENSIONS[extension].extends
        for member in EXTENSIONS[extension].defs[EXTENSIONS[extension].extends[schema_name]].get("properties", {})
    )


def check_known(extensions):
    """A profile that offers an extension the proxy does not implement is refused, so the app does not start."""
    unknown = sorted(set(extensions) - set(EXTENSIONS))
    if unknown:
        raise ValueError(f"backend profile: unknown RPP extension {', '.join(unknown)}")
