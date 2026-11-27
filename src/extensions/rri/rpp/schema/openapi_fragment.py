"""The OpenAPI fragment of the rri extension: the paths of its request contacts (docs/rri/rri-extension.md). Core §16.1
derives every path from an object's Identifier (guidelines §5.7): `/requestContacts`, `/requestContacts/{id}` and
`/requestContacts/{id}/availability`. The OpenAPI document of the drafts has none of them, so they are made from the
paths of the contact, whose uniform interface a request contact shares (not its processes), with their own operationIds.
Their schemas are plain objects: the mappers validate with the schema of the extension.

The operationIds are `requestContacts_read` and so on, as the document of the drafts names the operations of the contact;
each operation names the module of its handler (`x-openapi-router-controller`)."""
import copy
import re

HANDLERS = "extensions.rri.rpp.handlers"

CONTROLLER = f"{HANDLERS}.request_contact_handlers"

# The paths of the contact an operation of the request contact is made from.
TEMPLATE = "contact"

IDENTIFIER = "requestContact"

SUFFIXES = ("", "/{id}", "/{id}/availability")

SCHEMA_REF = re.compile(r"^#/components/schemas/gen\.(\w+)(\.\w+)$")


def plural(identifier: str) -> str:
    """Core §16.1.1, for the identifiers here."""
    return f"{identifier}s"


def _renamed(node, schemas: dict):
    """The node of a path of the contact, for the request contact: its operationIds and schemas renamed, its descriptions
    left out, as they describe the contact, and its handler named."""
    if isinstance(node, list):
        return [_renamed(item, schemas) for item in node]
    if not isinstance(node, dict):
        return node
    renamed = {}
    for key, value in node.items():
        if key == "description" and isinstance(value, str) and "operationId" in node:
            continue
        if key == "operationId":
            value = value.replace(plural(TEMPLATE), plural(IDENTIFIER), 1)
        elif key == "$ref" and isinstance(value, str):
            match = SCHEMA_REF.fullmatch(value)
            if match and match.group(1) in (TEMPLATE, f"{TEMPLATE}Availability"):
                name = f"ext.{match.group(1).replace(TEMPLATE, IDENTIFIER, 1)}{match.group(2)}"
                schemas[name] = {"type": "object", "description": "Validated with the schema of the extension"}
                value = f"#/components/schemas/{name}"
        renamed[key] = _renamed(value, schemas)
    if "operationId" in renamed:
        renamed["x-openapi-router-controller"] = CONTROLLER
    return renamed


def openapi_fragment(drafts: dict) -> dict:
    """The paths and the schemas the extension adds to the OpenAPI document `drafts`, which it reads and does not change."""
    schemas: dict = {}
    paths = {}
    for suffix in SUFFIXES:
        path = copy.deepcopy(drafts["paths"][f"/{plural(TEMPLATE)}{suffix}"])
        paths[f"/{plural(IDENTIFIER)}{suffix}"] = _renamed(path, schemas)
    return {"paths": paths, "components": {"schemas": schemas}}
