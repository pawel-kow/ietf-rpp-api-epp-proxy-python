"""The extensions an extension depends on without saying so: those whose definitions its own definitions refer to.

An Extension Schema refers to a base definition by `{"$ref": "#/$defs/<name>"}` (json §4.10). A name that is none of the extension's
own and none of the base's is a definition of another extension (the Component Objects of `io.github.pawel-kow.rpp.messages` that the
message types of other extensions use), and the extension is only valid in a preset that contains that one. There is no member of
`rpp:extension` for it (.spec/spec-issues.md, "An extension that uses the definitions of another extension")."""
from rpp.schema.bundle_definitions import bundle_definitions
from rpp.schema.rpp_extension import RppExtension

_DEF = "#/$defs/"


def _refs(node):
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith(_DEF):
            yield ref[len(_DEF):]
        for value in node.values():
            yield from _refs(value)
    elif isinstance(node, list):
        for value in node:
            yield from _refs(value)


def foreign_references(extension: RppExtension, others) -> dict[str, RppExtension]:
    """The definitions of another extension (of `others`) that the definitions of the extension refer to: each name, with the
    extension that defines it. A name that nothing defines is not among them."""
    found = {}
    for name in dict.fromkeys(_refs(extension.defs)):
        if name in extension.defs or name in bundle_definitions():
            continue
        owner = next((other for other in others if other.id != extension.id and name in other.defs), None)
        if owner is not None:
            found[name] = owner
    return found
