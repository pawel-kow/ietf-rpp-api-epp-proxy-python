"""docs/rri/rri-extension.md against the schema of the extension: every example marked `<!-- example valid|invalid
<definition> -->` validates, or fails, against the Effective Schema of a server that supports the extension, as
guidelines §9 requires of an extension specification, and every definition it shows (`<!-- definition <name> -->`)
is the one of .spec/rri-extension.schema.json."""
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

DOC = (ROOT / "docs" / "rri" / "rri-extension.md").read_text(encoding="utf-8")

SCHEMA = json.loads((ROOT / ".spec" / "rri-extension.schema.json").read_text(encoding="utf-8"))

EXAMPLE = re.compile(r"<!-- example (valid|invalid) ([\w.]+) -->\n```json\n(.*?)```", re.DOTALL)

DEFINITION = re.compile(r"<!-- definition ([\w.]+) -->\n```json\n(.*?)```", re.DOTALL)

EXAMPLES = [pytest.param(kind, schema, json.loads(body), id=f"{n}-{kind}-{schema}")
            for n, (kind, schema, body) in enumerate(EXAMPLE.findall(DOC), start=1)]

DEFINITIONS = [pytest.param(name, json.loads(body), id=name) for name, body in DEFINITION.findall(DOC)]


def test_the_document_has_valid_and_invalid_examples():
    assert {param.values[0] for param in EXAMPLES} == {"valid", "invalid"}


@pytest.mark.parametrize("kind, schema, example", EXAMPLES)
def test_an_example_validates_as_it_says(kind, schema, example):
    if kind == "valid":
        validate_schema(schema, example, extensions=RRI_PROFILE.extensions)
    else:
        with pytest.raises(ValidationError):
            validate_schema(schema, example, extensions=RRI_PROFILE.extensions)


def test_the_document_shows_every_definition_of_the_schema():
    assert sorted(param.values[0] for param in DEFINITIONS) == sorted(SCHEMA["$defs"])


@pytest.mark.parametrize("name, shown", DEFINITIONS)
def test_a_definition_is_the_one_of_the_schema(name, shown):
    assert shown == {"$defs": {name: SCHEMA["$defs"][name]}}


def test_the_mapping_and_the_overview_are_those_of_the_schema():
    blocks = [json.loads(body) for body in re.findall(r"```json\n(.*?)```", DOC, re.DOTALL)]

    assert {"rpp:extends": SCHEMA["rpp:extends"]} in blocks
    assert {"rpp:extension": SCHEMA["rpp:extension"]} in blocks
    assert {"rpp:messages": SCHEMA["rpp:messages"]} in blocks


def test_the_document_is_ascii():
    assert DOC.isascii()
