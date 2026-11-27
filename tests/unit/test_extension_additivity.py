"""The Extension Schema check is a whitelist (json §Extension Framework, #178 review): no keyword the check did not list can let a
schema that constrains the base object pass. Every input of the review rounds is refused."""
import json
from pathlib import Path

import pytest

from rpp.schema.bundle_definitions import bundle_definitions
from rpp.schema.extension_additivity import check_additive
from rpp.schema.extensions import EXTENSIONS, _from_schema
from rpp.schema.rpp_extension import RppExtension


def extension(**sub):
    return RppExtension(id="x", name="x", version="1.0", url="https://x", extends={"domainName.create": "ext.x"},
                        defs={"ext.x": {"type": "object", **sub}})


A = {"properties": {"a": {}}}


@pytest.mark.parametrize("sub, keyword", [
    ({**A, "not": {}}, "not"),
    ({**A, "not": {"type": "object"}}, "not"),
    ({**A, "not": {"minProperties": 0}}, "not"),
    ({**A, "not": {"required": ["a"]}}, "not"),                       # stricter than json: not over own members
    ({**A, "if": {"maxProperties": 3}, "then": False}, "maxProperties|the schema false"),
    ({**A, "anyOf": [{"type": "string"}]}, "type 'string'"),
    ({**A, "allOf": [{"type": "string"}]}, "type 'string'"),
    ({**A, "const": {}}, "const"),
    ({**A, "enum": [{"a": 1}]}, "enum"),
    ({**A, "allOf": [False]}, "the schema false"),
    ({**A, "oneOf": [{}, {}]}, "oneOf"),
    ({**A, "oneOf": [{"required": ["a"]}, {"required": ["b"]}]}, "oneOf"),
    ({**A, "allOf": []}, "an empty allOf"),
    ({**A, "anyOf": []}, "an empty anyOf"),
    ({**A, "additionalProperties": False}, "additionalProperties"),
    ({**A, "unevaluatedProperties": {"type": "string"}}, "unevaluatedProperties"),
    ({**A, "propertyNames": {"maxLength": 3}}, "propertyNames"),
    ({**A, "minProperties": 1}, "minProperties"),
    ({**A, "maxProperties": 3}, "maxProperties"),
    ({**A, "allOf": [{"required": ["authInfo"]}]}, "required, naming authInfo"),
    ({**A, "anyOf": [{"properties": {"name": {"maxLength": 3}}}]}, "properties, naming name"),
    ({**A, "then": {"required": ["name"]}}, "required, naming name"),
    ({**A, "if": {"required": ["authInfo"]}, "then": {}}, "required, naming authInfo"),
    ({**A, "dependentSchemas": {"a": {"properties": {"name": {}}}}}, "properties, naming name"),
    ({**A, "dependentSchemas": {"a": {"not": {}}}}, "not"),
    ({**A, "dependentSchemas": {"name": {}}}, "dependentSchemas, naming name"),
    ({**A, "dependentRequired": {"a": ["authInfo"]}}, "dependentRequired, naming authInfo"),
    ({**A, "required": ["b"]}, "required, naming b"),
    ({**A, "patternProperties": {"^auth": {"type": "string"}}}, r"patternProperties '\^auth'"),
    ({"properties": {"name": {}}}, "declares name"),
    ({**A, "contains": {}}, "contains"),
    ({**A, "$ref": "#/$defs/x"}, r"\$ref"),
    ({**A, "rpp:constraints": {"x": "y"}}, "rpp:constraints"),
    ({**A, "allOf": [{"rpp:constraints": {"x": "y"}}]}, "rpp:constraints"),
])
def test_an_extension_schema_that_could_constrain_the_base_stops_the_server(sub, keyword):
    with pytest.raises(ValueError, match=f"The extension x, definition ext.x .*({keyword})"):
        check_additive(extension(**sub))


@pytest.mark.parametrize("sub", [
    {"properties": {"a": {"type": "string"}}, "required": ["a"]},
    {"properties": {"a": {}, "b": {}}, "dependentRequired": {"a": ["b"]}},
    {**A, "patternProperties": {"^x-": {"type": "string"}}},
    {"properties": {"a": {}, "b": {}}, "if": {"required": ["a"]}, "then": {"required": ["b"]}},
    {"properties": {"a": {}, "b": {}}, "dependentSchemas": {"a": {"required": ["b"]}}},
    {"properties": {"a": {}, "b": {}}, "anyOf": [{"required": ["a"]}, {"required": ["b"]}], "additionalProperties": True},
    {"properties": {"a": {}}, "allOf": [True, {"required": ["a"]}], "title": "t", "description": "d", "rpp:note": 1},
])
def test_an_extension_schema_that_only_adds_is_accepted(sub):
    check_additive(extension(**sub))


def test_the_extensions_of_the_proxy_are_additive():
    for known in EXTENSIONS.values():
        check_additive(known)
    paths = list(Path("src/extensions").rglob("*-extension.schema.json"))
    loaded = [_from_schema(json.loads(path.read_text(encoding="utf-8"))) for path in paths]
    definitions = {**bundle_definitions(), **{name: schema for item in loaded for name, schema in item.defs.items()}}
    for item in loaded:
        check_additive(item, definitions)


def test_the_document_of_an_extension_schema_has_no_rpp_constraints():
    document = {"$id": "https://x", "rpp:extension": {"id": "x", "name": "x", "version": "1.0"}, "rpp:extends": {},
                "$defs": {}, "rpp:constraints": {"x": "y"}}

    with pytest.raises(ValueError, match="The Extension Schema of x contains rpp:constraints"):
        _from_schema(document)


OWNER = "https://example.org/owner.schema.json"


def owned(**sub):
    """An extension that extends `thing.create` of the extension `owner`."""
    return RppExtension(id="x", name="x", version="1.0", url="https://x", extends={"thing.create": "ext.x"},
                        owners={"thing.create": OWNER}, defs={"ext.x": {"type": "object", **sub}})


OWNER_DEFS = {"thing.create": {"type": "object", "properties": {"id": {}, "kind": {}}}}


def test_an_extension_of_another_extension_is_checked_against_the_definition_of_the_owner():
    check_additive(owned(properties={"a": {}}), OWNER_DEFS)
    with pytest.raises(ValueError, match="declares kind, which thing.create declares"):
        check_additive(owned(properties={"kind": {}}), OWNER_DEFS)
    with pytest.raises(ValueError, match="required, naming id"):
        check_additive(owned(properties={"a": {}}, required=["id"]), OWNER_DEFS)


def test_the_key_of_a_definition_of_another_extension_is_its_schema_and_the_definition():
    document = {"$id": "https://x", "rpp:extension": {"id": "x", "name": "x", "version": "1.0"},
                "rpp:extends": {f"{OWNER}#/$defs/thing.create": "#/$defs/ext.x", "#/$defs/domainName.create": "#/$defs/ext.y"},
                "$defs": {"ext.x": {}, "ext.y": {}}}

    loaded = _from_schema(document)

    assert loaded.extends == {"thing.create": "ext.x", "domainName.create": "ext.y"}
    assert loaded.owners == {"thing.create": OWNER}


def test_a_key_without_a_schema_must_name_a_definition_of_rpp():
    document = {"$id": "https://x", "rpp:extension": {"id": "x", "name": "x", "version": "1.0"},
                "rpp:extends": {"#/$defs/thing.create": "#/$defs/ext.x"}, "$defs": {"ext.x": {}}}

    with pytest.raises(ValueError, match=r"The extension x extends thing.create, which RPP does not define.*<\$id of the owner>#/\$defs/thing.create"):
        _from_schema(document)
