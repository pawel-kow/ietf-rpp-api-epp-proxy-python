"""The definition each body schema of the OpenAPI document stands for (#204). A body schema of the drafts is
`#/components/schemas/gen.<definition>`, one of an extension's object `ext.<definition>`; the definition is named as the mappers
validate with it (`domainName.create`, `planet.create`: an object of a registered extension). The routing spec marks each such schema with
`x-rpp-definition` next to its `$ref`, which Connexion keeps when it resolves the reference, so that the body validators validate
with the definition of the request's preset, and the document served points the body at the preset's definition."""
import re

MARKER = "x-rpp-definition"

_BODY_REF = re.compile(r"^#/components/schemas/(?:gen|ext)\.(\w+\.\w+)$")


def definition_of(ref) -> str | None:
    """The definition a body schema reference names, None for one of no definition (`protocol.PartialUpdate`)."""
    match = _BODY_REF.fullmatch(ref) if isinstance(ref, str) else None
    return match.group(1) if match else None


def body_schemas(spec: dict):
    """Each body schema of an operation that is a reference, also the items of an array body: the nodes the marker goes on."""
    for item in spec["paths"].values():
        for operation in item.values():
            if not isinstance(operation, dict):
                continue
            contents = [operation.get("requestBody", {}).get("content", {})]
            contents += [response.get("content", {}) for response in operation.get("responses", {}).values()
                         if isinstance(response, dict)]
            for content in contents:
                for media in content.values():
                    schema = media.get("schema")
                    if isinstance(schema, dict) and isinstance(schema.get("items"), dict):
                        schema = schema["items"]
                    if isinstance(schema, dict) and "$ref" in schema:
                        yield schema


def mark_body_definitions(spec: dict, known) -> dict:
    """Marks each body schema whose definition is among `known` (the definitions some offered preset has)."""
    for schema in body_schemas(spec):
        name = definition_of(schema["$ref"])
        if name is not None and name in known:
            schema[MARKER] = name
    return spec
