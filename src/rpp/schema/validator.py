import json
import os

from jsonschema import Draft202012Validator

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), 'schemas', 'rpp.schema.normalized.json')

with open(SCHEMA_FILE) as f:
    _bundle = json.load(f)


def _validator_for(schema_name):
    return Draft202012Validator({"$ref": f"#/$defs/{schema_name}", "$defs": _bundle["$defs"]})


validators = {name: _validator_for(name) for name in _bundle["$defs"]}


def validate_schema(schema_name, data):
    validators[schema_name].validate(data)
