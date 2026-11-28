"""The paths of the data objects an offered extension defines. Core §16.1 derives every path from an object's
Identifier (guidelines §5.7). The OpenAPI document is generated from the drafts and has none of them, so each registered
extension brings the fragment of its own (`add_registered_paths`), built from the document where its objects share the
uniform interface of a base object. Their schemas in the OpenAPI document are plain objects: the mappers validate with the
extension's schema."""
import json
import re

from registration import ExtensionRegistry
from rpp.schema.extensions import EXTENSIONS


def plural(identifier: str) -> str:
    """Core §16.1.1, for the identifiers here: `es` after an `s` (`authInfoProcess` is `authInfoProcesses`)."""
    return f"{identifier}es" if identifier.endswith("s") else f"{identifier}s"


# The data objects of the drafts that have paths of their own.
DRAFT_OBJECTS = ("domainName", "contact", "host", "organisation")


def collections(extensions) -> dict[str, str]:
    """The first path segment of each data object, of the drafts and of the offered extensions, and the object it addresses."""
    return {plural(obj): obj for obj in (*DRAFT_OBJECTS, *(obj for ext in extensions for obj in EXTENSIONS[ext].objects))}


# The path segments of the Process Objects of an extension, after `/domainNames/{name}/processes/`.
PROCESS_SEGMENT = re.compile(r"^/?[^/]+/[^/]+/processes/([^/]+)")


def process_owners(extensions) -> dict[str, str]:
    """The path segment of each Process Object the extensions add to a data object, and the extension that defines it."""
    return {plural(process): ext for ext in extensions for process in EXTENSIONS[ext].processes}


def process_segment(path: str) -> str | None:
    """The path segment of the process a path addresses (`authInfoProcesses` in `/domainNames/x/processes/authInfoProcesses/latest`),
    None for a path that is not one of a process of an object."""
    match = PROCESS_SEGMENT.match(path)
    return match.group(1) if match else None


def add_registered_paths(spec: dict, registry: ExtensionRegistry) -> dict:
    """Adds the OpenAPI fragment (paths and schemas) of each extension the app registered. Only a registered extension
    has paths: an app built without it has none, and no operationId that points at its handlers. A path or schema two
    fragments, or a fragment and the document, both define is a configuration error."""
    for extension in registry:
        if extension.openapi is None:
            continue
        fragment = json.loads(json.dumps(extension.openapi(spec)))  # a copy of its own, nothing of it shared
        for path, item in fragment["paths"].items():
            if path in spec["paths"]:
                raise ValueError(f"The extension {extension.id} defines the path {path}, which exists")
            spec["paths"][path] = item
        for name, schema in fragment.get("components", {}).get("schemas", {}).items():
            if name in spec["components"]["schemas"] and spec["components"]["schemas"][name] != schema:
                raise ValueError(f"The extension {extension.id} defines the schema {name}, which differs from one that exists")
            spec["components"]["schemas"][name] = schema
    return spec
