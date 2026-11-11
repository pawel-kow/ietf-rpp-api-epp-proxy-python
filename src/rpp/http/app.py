import copy
from functools import cache
from pathlib import Path

import yaml
from connexion import FlaskApp
from connexion.datastructures import MediaTypeDict
from connexion.exceptions import ProblemException
from connexion.middleware import MiddlewarePosition
from connexion.resolver import RelativeResolver
from connexion.validators import VALIDATOR_MAP
from starlette.middleware.cors import CORSMiddleware
from rpp.http.problem import handle_rpp_error
from rpp.http.middleware.body_buffering_middleware import BodyBufferingMiddleware
from rpp.http.validators.rpp_request_body_validator import RppRequestBodyValidator
from rpp.http.validators.rpp_response_body_validator import RppResponseBodyValidator
from rpp.http.security.session_security_handler import SessionSecurityHandler
from core.capabilities.backend_profile import BackendProfile
from rpp.mapping.domain.idn_tables import IdnTables

OPENAPI_SPEC = Path(__file__).parent.parent / "openapi.yaml"


@cache
def parsed_spec() -> dict:
    """
    The OpenAPI document, parsed once per process with libyaml, because parsing it takes most of the time an app
    takes to build (#112). Callers get it shared: copy it before handing it on.
    """
    with OPENAPI_SPEC.open("rb") as spec:
        return yaml.load(spec, Loader=yaml.CSafeLoader)


def create_app(sessions, profile: BackendProfile, discovery_settings=None, idn_tables=None):
    """
    Builds the application.

    Args:
        sessions: The `SessionPool`, which gives the registry backend of the request's user, or None to reject the
            request.
        profile: What the backend can hold, which the mappers check, refusals name and discovery states.
        discovery_settings: Has rpp_base_url, rpp_tlds, rpp_environment_name and
            rpp_environment_status, which the discovery document states.
        idn_tables: The IdnTables that map a domain's `lgr` to the IDN table of EPP. Without them no `lgr` is
            accepted, and reads leave out `uName` and `lgr`.
    """
    app = FlaskApp(
        __name__,
        security_map={"basic": lambda: SessionSecurityHandler(sessions)},
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
    # connexion changes the spec it is given, so each app gets its own copy.
    app.add_api(copy.deepcopy(parsed_spec()), resolver=RelativeResolver('rpp.handlers'), resolver_error=501,
                validate_responses=True, options={"swagger_ui": True, "serve_spec": True},
                validator_map={
                    "body": MediaTypeDict({**VALIDATOR_MAP["body"], "*/*json": RppRequestBodyValidator}),
                    "response": MediaTypeDict({"*/*json": RppResponseBodyValidator}),
                })
    app.app.config["RPP_DISCOVERY_SETTINGS"] = discovery_settings
    app.app.config["RPP_IDN_TABLES"] = idn_tables or IdnTables()
    app.app.config["RPP_BACKEND_PROFILE"] = profile
    app.add_error_handler(ProblemException, handle_rpp_error)

    return app
