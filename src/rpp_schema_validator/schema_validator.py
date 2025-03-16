from jsonschema import validate
import os
import json

schemas = {}
path = os.path.join(os.path.dirname(__file__), 'schemas')
for schema in os.listdir(path):
    with open(os.path.join(path, f'{schema}')) as f:
        if schema.endswith('.json'):
            schema_name = schema[:-5]  # Remove the .json extension
            schemas[schema_name] = json.load(f)

def validate_schema(schema_name, data):
    validate(data, schemas[schema_name])
