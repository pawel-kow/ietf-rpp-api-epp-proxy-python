import jsonschema
from connexion.exceptions import NonConformingResponseBody
from connexion.validators import JSONResponseBodyValidator

from rpp.http.body_definitions import MARKER
from rpp.http.preset_middleware import REQUEST_SCHEMAS


class RppResponseBodyValidator(JSONResponseBodyValidator):
    """Validates a response body, which RPP allows to be absent (delete has output cardinality 0-1).

    A body that stands for a definition (`x-rpp-definition`, #204) is validated with that definition of the preset the
    response is under, without its profiles (a response is never validated with them); an array body item by item. An object of
    an extension the request preset has and the response preset lacks is rendered under the request preset, and validated with
    it. Any other body is validated with its schema in the OpenAPI document, as Connexion does."""

    def _validate(self, body):
        if body is None:
            return
        array = self._schema.get("type") == "array" and isinstance(self._schema.get("items"), dict)
        name = (self._schema["items"] if array else self._schema).get(MARKER)
        if array and name is None and self._schema.get(MARKER):
            # an array that is a definition itself (`message.query`): its items are of definitions by reference, as the preset has them
            name, array = self._schema[MARKER], False
        schemas = self._scope.get("extensions", {}).get("connexion_context", {}).get(REQUEST_SCHEMAS)
        if name is None or schemas is None:
            super()._validate(body)
            return
        if array and not isinstance(body, list):
            raise NonConformingResponseBody(detail="Response body does not conform to specification: not an array")
        scope = schemas.response if schemas.response.has(name) else schemas.request
        try:
            for item in (body if array else [body]):
                scope.validate(name, item)
        except (jsonschema.ValidationError, ValueError):
            # Not the message: it would print the response, which may hold an authInfo.
            raise NonConformingResponseBody(
                detail=f"Response body does not conform to the definition {name} of the preset") from None
