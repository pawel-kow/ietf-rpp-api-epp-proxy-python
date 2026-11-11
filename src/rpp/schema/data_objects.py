import os

import yaml

DATA_OBJECTS_FILE = os.path.join(os.path.dirname(__file__), 'schemas', 'draft-ietf-rpp-data-objects.yaml')

DEFAULT_VISIBILITY = "default"

with open(DATA_OBJECTS_FILE) as f:
    _model = yaml.safe_load(f)

# The top-level data elements of each object of the data model, with their Visibility (data-objects §2.4).
_visibility = {
    obj["identifier"]: {element["identifier"]: element.get("visibility") or DEFAULT_VISIBILITY for element in obj["elements"]}
    for section in ("components", "processes", "resources") for obj in _model[section]
}


def visibility_of(object_identifier: str) -> dict[str, str]:
    """The Visibility of each top-level data element of the object, by Identifier."""
    return _visibility[object_identifier]
