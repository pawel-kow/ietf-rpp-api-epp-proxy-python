from connexion import FlaskApp
from connexion.datastructures import MediaTypeDict
from connexion.exceptions import ProblemException
from connexion.lifecycle import ConnexionRequest, ConnexionResponse
from connexion.middleware import MiddlewarePosition
from connexion.problem import problem
from connexion.resolver import RelativeResolver
from connexion.validators import VALIDATOR_MAP
from starlette.middleware.cors import CORSMiddleware
from controller import *
from controller.helper.rpp_response import RPP_ERROR_TYPE, problem_headers
from controller.body_buffering_middleware import BodyBufferingMiddleware
from controller.rpp_request_body_validator import RppRequestBodyValidator
from controller.rpp_response_body_validator import RppResponseBodyValidator
from controller.epp_basic_security_handler import EppBasicSecurityHandler
from models import ResultCode
from rpp_to_model_mapper import IdnTables


def _default_result(status: int) -> ResultCode:
    if status >= 500:
        return ResultCode.UNIMPLEMENTED_COMMAND if status == 501 else ResultCode.COMMAND_FAILED
    return ResultCode.AUTHENTICATION_ERROR if status == 401 else ResultCode.COMMAND_SYNTAX_ERROR


def handle_rpp_error(request: ConnexionRequest, exc: ProblemException) -> ConnexionResponse:
    """Renders every error as a core §9 Problem Detail with the RPP response headers."""
    headers = {**problem_headers(_default_result(exc.status)), **(exc.headers or {})}
    if "RPP-Cltrid" in request.headers:
        headers["RPP-Cltrid"] = request.headers["RPP-Cltrid"]
    return problem(
        title=exc.title,
        detail=exc.detail,
        status=exc.status,
        type=RPP_ERROR_TYPE,
        instance=exc.instance,
        headers=headers,
        ext={"errors": [{
            "type": RPP_ERROR_TYPE,
            "result": headers["RPP-Code"],
            "reason": exc.detail or exc.title,
        }]},
    )


def create_app(authenticator, discovery_settings=None, idn_tables=None):
    """
    Builds the application.

    Args:
        authenticator: Provides authenticate(username, password), which returns the
            token info holding the request's EPP client, or None to reject the request.
        discovery_settings: Has rpp_base_url, rpp_tlds, rpp_environment_name and
            rpp_environment_status, which the discovery document states.
        idn_tables: The IdnTables that map a domain's `lgr` to the IDN table of EPP. Without them no `lgr` is
            accepted, and reads leave out `uName` and `lgr`.
    """
    app = FlaskApp(
        __name__,
        security_map={"basic": lambda: EppBasicSecurityHandler(authenticator.authenticate)},
    )
    app.add_middleware(BodyBufferingMiddleware, position=MiddlewarePosition.BEFORE_VALIDATION)
    app.add_middleware(
        CORSMiddleware,
        position=MiddlewarePosition.BEFORE_EXCEPTION,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_api("openapi.yaml", resolver=RelativeResolver('controller'), resolver_error=501,
                validate_responses=True, options={"swagger_ui": True, "serve_spec": True},
                validator_map={
                    "body": MediaTypeDict({**VALIDATOR_MAP["body"], "*/*json": RppRequestBodyValidator}),
                    "response": MediaTypeDict({"*/*json": RppResponseBodyValidator}),
                })
    app.app.config["RPP_DISCOVERY_SETTINGS"] = discovery_settings
    app.app.config["RPP_IDN_TABLES"] = idn_tables or IdnTables()
    app.add_error_handler(ProblemException, handle_rpp_error)

    return app
