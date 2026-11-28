"""docs/extensions/<name>-extension.md against the schema of the extension: every example marked `<!-- example valid|invalid
<definition> -->` validates, or fails, against the Effective Schema of a server that supports the extensions, as guidelines §9
requires of an extension specification, and every definition a document shows (`<!-- definition <name> -->`) is the one of
.spec/<name>-extension.schema.json."""
import json
import re
from pathlib import Path

import pytest
from jsonschema import ValidationError

from rpp.schema.validator import validate_schema
from tests.helper.profiles import RRI_PROFILE

# the tests map without an app, so a validator is built on first use (tests/conftest.py)
pytestmark = pytest.mark.lazy_schemas

ROOT = Path(__file__).parents[2]

NAMES = ("messages", "domain-lock", "registry-changes")

EXAMPLE = re.compile(r"<!-- example (valid|invalid) ([\w.]+) -->\n```json\n(.*?)```", re.DOTALL)

DEFINITION = re.compile(r"<!-- definition ([\w.]+) -->\n```json\n(.*?)```", re.DOTALL)


def document(name: str) -> str:
    return (ROOT / "docs" / "extensions" / f"{name}-extension.md").read_text(encoding="utf-8")


def schema(name: str) -> dict:
    return json.loads((ROOT / ".spec" / f"{name}-extension.schema.json").read_text(encoding="utf-8"))


EXAMPLES = [pytest.param(name, kind, definition, json.loads(body), id=f"{name}-{n}-{kind}-{definition}")
            for name in NAMES for n, (kind, definition, body) in enumerate(EXAMPLE.findall(document(name)), start=1)]

DEFINITIONS = [pytest.param(name, definition, json.loads(body), id=f"{name}-{definition}")
               for name in NAMES for definition, body in DEFINITION.findall(document(name))]


@pytest.mark.parametrize("name", NAMES)
def test_the_document_is_ascii(name):
    assert document(name).isascii()


@pytest.mark.parametrize("name", NAMES)
def test_the_document_has_valid_and_invalid_examples(name):
    assert {param.values[1] for param in EXAMPLES if param.values[0] == name} == {"valid", "invalid"}


@pytest.mark.parametrize("name, kind, definition, example", EXAMPLES)
def test_an_example_validates_as_it_says(name, kind, definition, example):
    if kind == "valid":
        validate_schema(definition, example, extensions=RRI_PROFILE.extensions)
    else:
        with pytest.raises(ValidationError):
            validate_schema(definition, example, extensions=RRI_PROFILE.extensions)


@pytest.mark.parametrize("name", NAMES)
def test_the_document_shows_every_definition_of_the_schema(name):
    shown = sorted(param.values[1] for param in DEFINITIONS if param.values[0] == name)

    assert shown == sorted(schema(name)["$defs"])


@pytest.mark.parametrize("name, definition, shown", DEFINITIONS)
def test_a_definition_is_the_one_of_the_schema(name, definition, shown):
    assert shown == {"$defs": {definition: schema(name)["$defs"][definition]}}


@pytest.mark.parametrize("name", NAMES)
def test_the_mapping_and_the_overview_are_those_of_the_schema(name):
    blocks = [json.loads(body) for body in re.findall(r"```json\n(.*?)```", document(name), re.DOTALL)]
    spec = schema(name)

    assert {"rpp:extension": spec["rpp:extension"]} in blocks
    if spec["rpp:extends"]:
        assert {"rpp:extends": spec["rpp:extends"]} in blocks
    if "rpp:messages" in spec:
        assert {"rpp:messages": spec["rpp:messages"]} in blocks


@pytest.mark.parametrize("name", NAMES)
def test_the_schema_copy_of_the_package_is_the_one_of_the_spec(name):
    package = name.replace("-", "_")

    copy = ROOT / "src" / "extensions" / package / "rpp" / "schema" / f"{name}-extension.schema.json"

    assert json.loads(copy.read_text(encoding="utf-8")) == schema(name)
