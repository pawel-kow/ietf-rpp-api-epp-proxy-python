from jsonschema import validate
import os
import json
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from jsonschema import Draft202012Validator

registry = Registry()
schemas = {}
path = os.path.join(os.path.dirname(__file__), 'schemas')
for schema in os.listdir(path):
    with open(os.path.join(path, f'{schema}')) as f:
        if schema.endswith('.json'):
            schema_name = schema[:-5]  # Remove the .json extension
            schema_loaded = json.load(f)
            schemas[schema_name] = schema_loaded
            resource=Resource.from_contents(schema_loaded)
            registry = resource @ registry
  
validators = {
    x: Draft202012Validator(schemas[x], registry=registry) for x in schemas
}

def validate_schema(schema_name, data):
    validators[schema_name].validate(data)