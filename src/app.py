from connexion import FlaskApp
from connexion.exceptions import ProblemException
from connexion.lifecycle import ConnexionRequest, ConnexionResponse
from connexion.middleware import MiddlewarePosition
from connexion.problem import problem
from connexion.resolver import RelativeResolver
from starlette.middleware.cors import CORSMiddleware
from controller import *
from controller.epp_basic_security_handler import EppBasicSecurityHandler
from models import ResultCode


def handle_rpp_error(request: ConnexionRequest, exc: Exception) -> ConnexionResponse:
    if isinstance(exc, ProblemException):
        exc.headers = exc.headers or {}
        exc.headers\
            .update({
                "RPP-clTRID": request.headers.get("RPP-clTRID")
            } if "RPP-clTRID" in request.headers else {})
        if "RPP-code" not in exc.headers and exc.status >= 500:
            exc.headers\
                .update({
                    "RPP-code": ResultCode.COMMAND_FAILED.value[0],
                    "RPP-code-text": ResultCode.COMMAND_FAILED.value[1]
                })
        elif "RPP-code" not in exc.headers and exc.status == 401:
            exc.headers\
                .update({
                    "RPP-code": ResultCode.AUTHORIZATION_ERROR.value[0],
                    "RPP-code-text": ResultCode.AUTHORIZATION_ERROR.value[1]})

        elif "RPP-code" not in exc.headers and exc.status >= 400 and exc.status < 500:
            exc.headers\
                .update({
                    "RPP-code": ResultCode.COMMAND_SYNTAX_ERROR.value[0],
                    "RPP-code-text": ResultCode.COMMAND_SYNTAX_ERROR.value[1]
                })
        return problem(
            title=exc.title,
            detail=exc.detail,
            status=exc.status,
            type=exc.type,
            instance=exc.instance,
            headers=exc.headers,
            ext=exc.ext
        )
    return problem(
        title="Internal Server Error",
        detail=f"An unexpected error occurred: {str(exc)}",
        status=500,
        headers={
            "RPP-code": ResultCode.COMMAND_FAILED[0],
            "RPP-code-text": ResultCode.COMMAND_FAILED[1]
        }.update({
            "RPP-clTRID": request.headers.get("RPP-clTRID")
        } if "RPP-clTRID" in request.headers else {})
    )


def create_app(authenticator):
    """
    Builds the application.

    Args:
        authenticator: Provides authenticate(username, password), which returns the
            token info holding the request's EPP client, or None to reject the request.
    """
    app = FlaskApp(
        __name__,
        security_map={"basic": lambda: EppBasicSecurityHandler(authenticator.authenticate)},
    )
    app.add_middleware(
        CORSMiddleware,
        position=MiddlewarePosition.BEFORE_EXCEPTION,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_api("openapi.yaml", resolver=RelativeResolver('controller'), resolver_error=501,
                options={"swagger_ui": True, "serve_spec": True, "validate_responses": True})
    app.add_error_handler(ProblemException, handle_rpp_error)
    return app
