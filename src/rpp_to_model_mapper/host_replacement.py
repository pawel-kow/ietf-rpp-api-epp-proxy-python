from models import Host
from rpp_schema_validator import validate_schema
from .common import parse_rpp
from .hosts import add_rpp_status, rpp_host_to_model
from .rpp_models import RPPHost


def rpp_to_model(rpp: dict) -> Host:
    """Converts a full update to the Host it asks for."""
    validate_schema("host.update", rpp)
    host_rpp = parse_rpp(RPPHost, rpp)
    host = rpp_host_to_model(host_rpp)
    host.status = []
    for status in host_rpp.status or []:
        add_rpp_status(status, host)
    return host
