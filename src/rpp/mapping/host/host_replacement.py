from core.model.host.host_replacement import HostReplacement
from rpp.dto.rpp_host import RPPHost
from rpp.mapping.host.hosts import replacement_from_rpp, require_own_ns
from rpp.mapping.shared.common import parse_rpp
from rpp.schema.validator import validate_schema


def rpp_to_model(host_name: str, rpp: dict) -> HostReplacement:
    """Converts a full update of the host `host_name` to the host it asks for."""
    validate_schema("host.update", rpp)
    host_rpp = parse_rpp(RPPHost, rpp)
    wanted = replacement_from_rpp(host_name, host_rpp)
    require_own_ns(host_rpp)
    return wanted
