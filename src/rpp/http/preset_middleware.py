from connexion import ProblemException

from core.result.result_code import ResultCode
from rpp.http.extension_paths import collections, plural, process_owners, process_segment
from rpp.http.headers import problem_headers
from rpp.http.request_presets import RequestPresets
from rpp.schema.extensions import EXTENSIONS

# The keys of the request context that hold the `PresetSelection` of the request, the signalling method that made it and the
# `RequestSchemas` of the selection (what the body validators and the mappers validate with).
SELECTED_PRESET = "rpp_preset"
SIGNALLING = "rpp_preset_signalling"
REQUEST_SCHEMAS = "rpp_request_schemas"

# The operation that reads the schema of a preset: a document in its native media type, outside preset signalling.
SCHEMA_OPERATION = "presets_schemaRead"


class PresetMiddleware:
    """Selects the preset of each request and refuses what it does not allow, before anything else of the application.

    The selected preset is put in the request context. A path of a data object of an extension that the preset does not
    contain is a 400 `02001`, like any content that does not conform to the preset (core RC4, the code the proxy gives to
    what fails the schema). A path of a data object the backend does not hold is a 501 `02307`: core §16.1.6 lets a server
    answer an endpoint it does not implement with 404 or 501, and 02307 is the unimplemented object service. A path no
    operation serves is the router's 404, with no preset selected. The response names the applied preset (core §Preset
    Signalling); the Problem Details that an outer error handler renders get it from `handle_rpp_error`. Paths of no object
    (`/messages`, discovery, presets, profiles) are always allowed. It runs after the authentication, so a request that is not
    authenticated is still a 401 and gives no hint of the presets.
    """

    def __init__(self, app, signalling, request_presets: RequestPresets, extensions):
        self.app = app
        # The objects an extension defines are in the plural of their identifier (core §16.1). Only those of the
        # offered extensions have paths: any other is a 404, as without the extension.
        self.owners = {plural(obj): ext for ext in extensions for obj in EXTENSIONS[ext].objects}
        self.collections = collections(extensions)
        # The same for the Process Objects an extension adds to an object (`/domainNames/{name}/processes/authInfoProcesses`).
        self.process_owners = process_owners(extensions)
        self.signalling = signalling
        self.request_presets = request_presets

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Only a routed operation selects a preset and is refused: a path no operation serves stays the 404 of
            # the router, and a 401 never gets here.
            routed = scope.get("extensions", {}).get("connexion_routing", {}).get("operation_id")
            if not routed or routed.endswith(SCHEMA_OPERATION):
                # A path no operation serves is the router's 404. The schema of a preset is a document in its native
                # media type (core RC7): no selection, no refusal, no preset in the response.
                await self.app(scope, receive, send)
                return
            selection = self.signalling.resolve(scope)
            context = scope.setdefault("extensions", {}).setdefault("connexion_context", {})
            context[SELECTED_PRESET] = selection
            context[SIGNALLING] = self.signalling
            context[REQUEST_SCHEMAS] = self.request_presets.schemas(selection)
            send = self.signalling.announce(send, selection)
            segment = scope["path"].lstrip("/").split("/", 1)[0]
            obj = self.collections.get(segment)
            if obj is not None:
                self._check_object(segment, obj, selection.request)
            process = process_segment(scope["path"])
            owner = self.process_owners.get(process)
            if owner is not None and owner not in selection.request.extension_ids:
                self._refuse_extension(selection.request, f"the {process} processes")
        await self.app(scope, receive, send)

    def _check_object(self, segment, obj, preset) -> None:
        owner = self.owners.get(segment)
        if owner is not None and owner not in preset.extension_ids:
            self._refuse_extension(preset, obj)
        if obj not in self.request_presets.profile_of(preset).objects:
            code = ResultCode.UNIMPLEMENTED_OBJECT_SERVICE
            raise ProblemException(
                status=501, title=code.value[1],
                detail=f"The preset {preset.id} has no {obj} object on this server", headers=problem_headers(code))

    @staticmethod
    def _refuse_extension(preset, what) -> None:
        code = ResultCode.COMMAND_SYNTAX_ERROR
        raise ProblemException(
            status=400, title=code.value[1],
            detail=f"The preset {preset.id} does not contain the extension of {what}", headers=problem_headers(code))
