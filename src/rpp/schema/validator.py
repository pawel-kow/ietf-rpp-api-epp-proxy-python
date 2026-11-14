import json
import os
from functools import cache

from jsonschema import Draft202012Validator

from rpp.schema.extensions import EXTENSIONS

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), 'schemas', 'rpp.schema.normalized.json')

with open(SCHEMA_FILE) as f:
    _bundle = json.load(f)

# The definitions of the bundle and of every extension: an extension's names start with `ext.` (json §7).
_defs = {**_bundle["$defs"], **{name: schema for extension in EXTENSIONS.values()
                                 for name, schema in extension.defs.items()}}


def _validator_for(schema_name):
    return Draft202012Validator({"$ref": f"#/$defs/{schema_name}", "$defs": _defs})


validators = {name: _validator_for(name) for name in _bundle["$defs"]}


@cache
def _effective_validator(schema_name: str, extensions: tuple[str, ...]):
    """The effective schema of json §7.2: the base definition and those the extensions add to it, with `allOf`."""
    added = [EXTENSIONS[extension].extends.get(schema_name) for extension in extensions]
    parts = [{"$ref": f"#/$defs/{name}"} for name in [schema_name, *added] if name]
    if len(parts) == 1:
        return validators[schema_name]
    return Draft202012Validator({"allOf": parts, "$defs": _defs})


def validate_schema(schema_name, data, extensions: tuple[str, ...] = ()):
    """Validates `data` against a definition of the bundle, composed with what the given extensions add to it."""
    _effective_validator(schema_name, tuple(extensions)).validate(data)
