"""The OpenAPI fragment of the planets extension: the paths of its objects (docs/demo/planets-extension.md, Endpoints),
which the drafts' document does not have. `create_app` merges it into the document of an app that registered the
extension. The schemas of its bodies are plain objects: the mappers validate with the schema of the extension, as for
every extension. Every operationId is a fully qualified function name of the handler package."""

HANDLERS = "extensions.planets.rpp.handlers"

PLANET = f"{HANDLERS}.planet_handlers"
PLANET_TRANSFER = f"{HANDLERS}.planet_transfer_handlers"
SATELLITE = f"{HANDLERS}.satellite_handlers"

PROBLEM = "#/components/schemas/protocol.ProblemDetail"
RPP_JSON = "application/rpp+json"

_HEADER_REFS = [f"#/components/parameters/protocol.RequestHeaders.{name}"
                for name in ("rppCltrid", "accept", "acceptLanguage", "rppAuthorization", "rppPreset")]
INCLUDE_ELEMENTS = "#/components/parameters/gen.IncludeElements"
IDENTIFIER = {"$ref": "#/components/schemas/gen.common.identifier"}

DESCRIPTIONS = {
    "400": "The server could not understand the request due to invalid syntax.",
    "401": "Access is unauthorized.",
    "403": "Access is forbidden.",
    "404": "The server cannot find the requested resource.",
    "406": "Client error",
    "409": "The request conflicts with the current state of the server.",
    "415": "The server refuses the content type of the request.",
    "422": "The request was well formed, but the server refused it.",
    "500": "Server error",
}

ERRORS_READ = ("400", "401", "403", "404", "406", "500")
ERRORS_CHANGE = ("400", "401", "403", "404", "406", "409", "415", "422", "500")
ERRORS_CREATE = ("400", "401", "403", "406", "409", "415", "422", "500")
ERRORS_ACTION = ("400", "401", "403", "404", "406", "409", "500")


def _headers(location: bool = False) -> dict:
    headers = {
        "RPP-Svtrid": {"required": True, "schema": {"type": "string"}},
        "RPP-Cltrid": {"required": True, "schema": {"type": "string"}},
        "RPP-Code": {"required": True, "description": "RPP result code, §18.", "schema": {"type": "string"}},
        "RPP-Queue-Size": {"required": False, "description": "Number of unacknowledged messages in the client's queue.",
                           "schema": {"type": "integer", "minimum": 0}},
        "RPP-Preset": {"required": False, "schema": {"type": "string"}},
        "Link": {"required": False, "description": "One `rel=\"rpp-process\"` link per process created as a side effect (§15).",
                 "schema": {"type": "array", "items": {"type": "string"}}},
    }
    if location:
        headers["Location"] = {"required": True, "schema": {"type": "string", "format": "uri"}}
    return headers


def _content(schema: str | dict | None, media: str = RPP_JSON) -> dict:
    if schema is None:
        return {}
    return {"content": {media: {"schema": {"$ref": schema} if isinstance(schema, str) else schema}}}


def _problem(status: str) -> dict:
    return {"description": DESCRIPTIONS[status], "headers": _headers(), **_content(PROBLEM, "application/problem+json")}


def _responses(success: dict, errors) -> dict:
    return {**success, **{status: _problem(status) for status in errors}}


def _path_parameters(*names: str) -> list:
    return [{"name": name, "in": "path", "required": True, "schema": IDENTIFIER} for name in names]


def _operation(operation_id: str, description: str, parameters: list, responses: dict, body: dict | None = None,
               tag: str = "Planet") -> dict:
    operation = {
        "operationId": operation_id,
        "description": description,
        "parameters": [*parameters, *({"$ref": ref} for ref in _HEADER_REFS)],
        "responses": responses,
        "tags": [tag],
        "security": [{"BasicAuth": []}, {"BearerAuth": []}],
    }
    if body is not None:
        operation["requestBody"] = body
    return operation


def _body(schema: str, required: bool = True) -> dict:
    return {"required": required, "content": {RPP_JSON: {"schema": {"$ref": schema}}}}


def _ok(schema: str | None, status: str = "200", location: bool = False, description: str = "The request has succeeded.") -> dict:
    return {status: {"description": description, "headers": _headers(location), **_content(schema)}}


def _availability(module: str, name: str, tag: str) -> dict:
    schema = f"#/components/schemas/ext.{name}Availability.read"
    parameters = [*_path_parameters("id"), {"$ref": INCLUDE_ELEMENTS}]
    unavailable = {"404": {"description": "The identifier is in use.", "headers": _headers(), **_content(schema)}}
    head = _responses(
        {"200": {"description": "The identifier is available.", "headers": _headers()},
         "404": {"description": "§16.4: HEAD reports with the status code alone.", "headers": _headers()}},
        ("400", "401", "403", "406", "500"))
    return {
        "head": _operation(f"{module}.{name}s_availabilityHead",
                           f"Whether a {name} with the identifier can be created, by the status code alone.",
                           parameters[:1], head, tag=tag),
        "get": _operation(f"{module}.{name}s_availability", f"Whether a {name} with the identifier can be created.",
                          parameters, _responses({**_ok(schema), **unavailable}, ("400", "401", "403", "406", "500")),
                          tag=tag),
    }


def _object_paths(module: str, name: str, tag: str, title: str) -> dict:
    read = f"#/components/schemas/ext.{name}.read"
    include = [{"$ref": INCLUDE_ELEMENTS}]
    one = _path_parameters("id")
    return {
        f"/{name}s": {
            "post": _operation(f"{module}.{name}s_create", f"Creates a {title}.", include,
                               _responses(_ok(read, "201", True, "A new resource has been created."), ERRORS_CREATE),
                               _body(f"#/components/schemas/ext.{name}.create"), tag),
        },
        f"/{name}s/{{id}}": {
            "get": _operation(f"{module}.{name}s_read", f"Reads a {title}.", [*one, *include],
                              _responses(_ok(read), ERRORS_READ), tag=tag),
            "put": _operation(f"{module}.{name}s_update", f"A full update of a {title}.", [*one, *include],
                              _responses(_ok(read), ERRORS_CHANGE), _body(f"#/components/schemas/ext.{name}.update"), tag),
            "patch": _operation(f"{module}.{name}s_updatePartial", f"A partial update of a {title}.", [*one, *include],
                                _responses(_ok(read), ERRORS_CHANGE), _body("#/components/schemas/protocol.PartialUpdate"),
                                tag),
            "delete": _operation(f"{module}.{name}s_delete", f"Deletes a {title}.", [*one, *include],
                                 _responses(_ok(read), ERRORS_ACTION), tag=tag),
        },
        f"/{name}s/{{id}}/availability": _availability(module, name, tag),
    }


def _transfer_paths() -> dict:
    base = "/planets/{id}/processes/transferProcesses"
    process = "#/components/schemas/gen.transferProcess.read"
    one = [*_path_parameters("id"), {"$ref": INCLUDE_ELEMENTS}]

    def operation(name: str, description: str, success: dict, errors, body: dict | None = None) -> dict:
        return _operation(f"{PLANET_TRANSFER}.planetTransferProcesses_{name}", description, one,
                          _responses(success, errors), body, "Planet")

    return {
        base: {"post": operation(
            "transferCreate", "Requests the transfer of a planet to the client, with the authorisation of the planet.",
            {**_ok(process), **_ok(process, "201", True, "The transfer is pending.")}, ERRORS_CHANGE,
            _body("#/components/schemas/gen.transferProcess.create"))},
        f"{base}/latest": {
            "get": operation("transferRead", "The latest transfer of the planet.", _ok(process), ERRORS_READ),
            "delete": operation("transferDelete", "Cancels the pending transfer, by its requester.", _ok(process),
                                ERRORS_ACTION),
        },
        f"{base}/latest/transferApprove": {
            "post": operation("transferApprove", "Approves the pending transfer, by the sponsor.", _ok(process),
                              ERRORS_ACTION)},
        f"{base}/latest/transferReject": {
            "post": operation("transferReject", "Rejects the pending transfer, by the sponsor.", _ok(process),
                              ERRORS_CHANGE, _body("#/components/schemas/gen.transferProcess.transferReject", False))},
    }


def _satellite_of_planet() -> dict:
    return {"/planets/{id}/satellites/{satelliteId}": {"get": _operation(
        f"{PLANET}.planets_satelliteRead", "Reads a satellite of the planet (Direct Access).",
        [*_path_parameters("id", "satelliteId"), {"$ref": INCLUDE_ELEMENTS}],
        _responses(_ok("#/components/schemas/ext.satellite.read"), ERRORS_READ), tag="Planet")}}


def openapi_fragment(drafts: dict) -> dict:
    """The paths and the schemas the extension adds to the OpenAPI document (it needs nothing of the document of the drafts, `drafts`)."""
    paths = {
        **_object_paths(PLANET, "planet", "Planet", "planet"),
        **_transfer_paths(),
        **_satellite_of_planet(),
        **_object_paths(SATELLITE, "satellite", "Satellite", "satellite"),
    }
    names = [f"ext.{name}.{kind}" for name in ("planet", "satellite") for kind in ("create", "read", "update")]
    names += ["ext.planetAvailability.read", "ext.satelliteAvailability.read"]
    schemas = {name: {"type": "object", "description": "Validated with the schema of the extension"} for name in names}
    return {"paths": paths, "components": {"schemas": schemas}}
