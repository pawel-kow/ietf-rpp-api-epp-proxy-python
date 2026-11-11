import functools

from connexion import ProblemException
from flask import request as flask_request
from jsonschema import ValidationError

from core.capabilities.not_supported_by_backend import NotSupportedByBackend
from core.capabilities.not_supported_by_proxy import NotSupportedByProxy
from core.capabilities.unsupported_feature import UnsupportedFeature
from rpp.http.context import backend_profile
from rpp.http.headers import problem_headers
from rpp.http.problem import http_status


def request_has_content() -> bool:
    """Whether the request carries content, whatever its framing, type or syntax: `null` and `{}` count.

    Read through Flask: Connexion's `get_body()` gives the parsed content, which is falsy for these,
    and waiting on the ASGI stream can hang when the body arrives after the headers. Form content
    types leave no raw bytes in the handler, so the parsed form and files count too.
    """
    return bool(
        flask_request.content_length or flask_request.get_data() or flask_request.form or flask_request.files
    )


def require_empty_body():
    """DELETE takes no request body (core §16.1.4)."""
    if request_has_content():
        raise ProblemException(status=400, title="Bad Request", detail="Request body must be empty for DELETE method")


def _unsupported_detail(e: UnsupportedFeature) -> str:
    """A mapper does not know the backend, so its refusal is named here."""
    if isinstance(e, (NotSupportedByBackend, NotSupportedByProxy)):
        return e.detail(backend_profile().name)
    return str(e)


def map_request(mapper, *args, **kwargs):
    """Runs an RPP to model mapper, translating what it rejects."""
    try:
        return mapper(*args, **kwargs)
    except UnsupportedFeature as e:
        raise ProblemException(
            status=http_status(e.code), title=e.code.value[1], detail=_unsupported_detail(e),
            headers=problem_headers(e.code),
        )
    except ValidationError as e:
        # Only the message: str(e) would print the request, including its authInfo.
        raise ProblemException(status=400, title="Bad Request", detail=e.message)
    except Exception as e:
        raise ProblemException(status=400, title="Bad Request", detail=str(e))


def rpp_operation(handler):
    """Answers anything a handler did not expect with a Problem Detail."""
    @functools.wraps(handler)
    def wrapper(*args, **kwargs):
        try:
            return handler(*args, **kwargs)
        except ProblemException:
            raise
        except Exception as e:
            raise ProblemException(status=500, title="Internal Server Error", detail=str(e))
    return wrapper
