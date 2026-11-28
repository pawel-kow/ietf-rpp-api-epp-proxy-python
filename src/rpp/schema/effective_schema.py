"""The effective schema of a preset at a server (json §Effective Schema, §Preset Schema): the definitions of the bundle, of the
extensions of the preset and of the Profile Schemas of its applicable profiles, each definition that extensions extend or
profiles constrain composed in place with `allOf` under the key of the base definition. What the Preset Schema publishes has
no `unevaluatedProperties`; what the proxy validates with has it injected at every object-schema node (json §4.9.1)."""
import copy

from rpp.schema.bundle_definitions import bundle_definitions
from rpp.schema.profile_constraints import ProfileConstraints

UNEVALUATED = "unevaluatedProperties"

# Schema keywords whose value is a schema, a list of schemas, or a map of schemas that the injection goes into. A node
# reached through `_IN_PLACE` is evaluated together with the node that holds the keyword, so the holder's
# `unevaluatedProperties` covers its members and the node itself gets none; its own `properties` and `items` are other
# nodes and are entered. `if` and `not` are conditions, not what an instance must be: an injection there would change
# what they match, so they are not entered.
_SCHEMA = ("items", "contains", "additionalProperties", "unevaluatedProperties")
_SCHEMAS = ("prefixItems",)
_SCHEMA_MAPS = ("properties", "patternProperties", "$defs")
_IN_PLACE = ("then", "else")
_IN_PLACE_LISTS = ("allOf", "anyOf", "oneOf")
_IN_PLACE_MAPS = ("dependentSchemas",)


def _inject(node, root: bool = True) -> None:
    """Puts the keyword at every object-schema node of `node` (`type` is `object`) that says nothing about members it does
    not declare: `unevaluatedProperties` or `additionalProperties` (free keys) already there stay as they are. `root` is
    False for a node the holder of an applicator covers: the node of a definition that is composed with `allOf`, and a
    branch of `allOf`, `anyOf`, `oneOf`, `then`, `else` or `dependentSchemas`."""
    if isinstance(node, list):
        for item in node:
            _inject(item)
        return
    if not isinstance(node, dict):
        return
    if root and node.get("type") == "object" and UNEVALUATED not in node and "additionalProperties" not in node:
        node[UNEVALUATED] = False
    for keyword in _SCHEMA:
        if isinstance(node.get(keyword), dict):
            _inject(node[keyword])
    for keyword in _SCHEMAS:
        if isinstance(node.get(keyword), list):
            for item in node[keyword]:
                _inject(item)
    for keyword in _SCHEMA_MAPS:
        if isinstance(node.get(keyword), dict):
            for value in node[keyword].values():
                _inject(value)
    for keyword in _IN_PLACE:
        if isinstance(node.get(keyword), dict):
            _inject(node[keyword], root=False)
    for keyword in _IN_PLACE_LISTS:
        if isinstance(node.get(keyword), list):
            for item in node[keyword]:
                _inject(item, root=False)
    for keyword in _IN_PLACE_MAPS:
        if isinstance(node.get(keyword), dict):
            for value in node[keyword].values():
                _inject(value, root=False)


def required_of(profile, required) -> frozenset:
    """The extensions a profile requires, directly or through its base profiles (`required`, by profile id); a profile
    constrains no definition of another extension."""
    if required is not None and profile.id in required:
        return frozenset(required[profile.id])
    return frozenset(reference.id for reference in profile.required_extensions)


def _refs(keys) -> list[dict]:
    return [{"$ref": f"#/$defs/{key}"} for key in keys]


def compose(extensions, profiles, inject: bool, required=None) -> dict:
    """The `$defs` of the effective schema of the extensions (`RppExtension`s) and the profiles (`RppProfile`s) of a preset.

    A definition an extension extends is the `allOf` of the base definition, in place, and the references to the extension's
    sub-schemas, then those of the profiles that constrain it; an extension sub-schema that a profile constrains is the `allOf`
    of itself, in place, and the references to the profile sub-schemas. Every sub-schema is also under its own key. With
    `inject`, the `unevaluatedProperties` of json §4.9.1 are added: at the holder of each `allOf`, so that a member that any
    branch declares is evaluated."""
    definitions = copy.deepcopy(bundle_definitions())
    extended: dict[str, list[str]] = {}
    branches = set()
    for extension in extensions:
        definitions.update(copy.deepcopy(extension.defs))
        for base, ext in extension.extends.items():
            extended.setdefault(base, []).append(ext)
            branches.add(ext)
    for extension in extensions:
        for message in ("message.read", "message.create"):
            data = definitions[message]["properties"]["data"]["oneOf"]
            data.extend(ref for ref in _refs(extension.messages.values()) if ref not in data)
    constrained: dict[str, list[str]] = {}
    for profile in profiles:
        if profile.schema is None:
            continue
        for name, schema in profile.schema.get("$defs", {}).items():
            definitions[name] = copy.deepcopy(schema)
            branches.add(name)
        for target, (_, subs) in ProfileConstraints.of(profile, required_of(profile, required)).targets.items():
            constrained.setdefault(target, []).extend(sub for sub in subs if sub not in constrained.get(target, []))
    holders = set(extended) | {target for target in constrained if target not in branches}
    if inject:
        for name, schema in definitions.items():
            _inject(schema, root=name not in branches and name not in holders)
    for target, subs in constrained.items():
        if target in branches:          # an extension sub-schema that a profile constrains, composed in place
            definitions[target] = {"allOf": [definitions[target], *_refs(subs)]}
    for target in holders:
        holder = {"allOf": [definitions[target], *_refs(extended.get(target, ())), *_refs(constrained.get(target, ()))]}
        if inject:
            holder[UNEVALUATED] = False
        definitions[target] = holder
    return definitions
