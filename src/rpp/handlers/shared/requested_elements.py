from flask import request as flask_request

from rpp.mapping.shared import include_elements
from rpp.http.operation import map_request


INCLUDE_ELEMENTS = "includeElements"


def requested_elements(object_identifier: str) -> frozenset[str]:
    """The data elements the request asks to include, one Identifier per repeated `includeElements` (core §16.1.7).
    Read from the query itself: the OpenAPI declares one comma-separated value (see spec-issues.md)."""
    return map_request(include_elements.rpp_to_model, object_identifier, flask_request.args.getlist(INCLUDE_ELEMENTS))
