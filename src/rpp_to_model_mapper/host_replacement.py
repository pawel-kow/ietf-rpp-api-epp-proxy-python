from models import Host
from rpp_schema_validator import validate_schema
from .common import parse_rpp
from .hosts import require_own_ns, rpp_host_with_status_to_model
from .rpp_models import RPPHost


def rpp_to_model(rpp: dict) -> Host:
    """Converts a full update to the Host it asks for."""
    validate_schema("host.update", rpp)
    host_rpp = parse_rpp(RPPHost, rpp)
    host = rpp_host_with_status_to_model(host_rpp)
    require_own_ns(host_rpp)
    return host
