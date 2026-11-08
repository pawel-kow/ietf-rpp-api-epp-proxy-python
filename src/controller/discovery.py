import logging
import uuid
from datetime import datetime, timezone

from flask import current_app
from connexion import ProblemException

import rpp_to_model_mapper as rpp_mapper
from models import Discovery, ResultCode
from .helper.rpp_response import RPP_MEDIA_TYPE, client_transaction_id, problem_headers, rpp_code, rpp_operation

logger = logging.getLogger(__name__)

# The RPP version of core §12, and the data objects (data-objects §17.2) the proxy implements.
RPP_VERSION = "1.0"
OBJECTS = ["domainName", "host", "contact"]
# The profile the proxy follows (core §12.4, data-objects §2.8, json §8.7.1). Its read, GET /profiles/{name}, is 501.
PROFILES = ["urn:ietf:params:rpp:profile:epp-compatibility"]



@rpp_operation
def discovery_read():
    """The Discovery Data Object: no authentication and no EPP, it comes from configuration and the proxy itself."""
    settings = current_app.config.get("RPP_DISCOVERY_SETTINGS")
    missing = rpp_mapper.discovery.invalid_settings(settings)
    if missing:
        logger.warning("Discovery is not configured, missing or invalid: %s", ", ".join(missing))
        raise ProblemException(
            status=500, title=ResultCode.COMMAND_FAILED.value[1], detail="The server is not configured to describe itself",
            headers=problem_headers(ResultCode.COMMAND_FAILED),
        )
    discovery = Discovery(
        version=RPP_VERSION,
        base_url=settings.rpp_base_url,
        tlds=list(settings.rpp_tlds),
        environment_name=settings.rpp_environment_name,
        environment_status=settings.rpp_environment_status,
        objects=OBJECTS,
        profiles=PROFILES,
        datetime=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    headers = {
        "Content-Type": RPP_MEDIA_TYPE,
        "RPP-Cltrid": client_transaction_id(),
        "RPP-Svtrid": str(uuid.uuid4()),
        "RPP-Code": rpp_code(ResultCode.COMMAND_COMPLETED_SUCCESSFULLY),
    }
    return rpp_mapper.discovery.model_to_rpp(discovery), 200, headers
