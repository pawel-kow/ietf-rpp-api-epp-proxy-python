from models import Discovery
from rpp_schema_validator import validate_schema
from .rpp_models import RPPDiscovery, RPPDiscoveryEnvironment, RPPDiscoveryVersion


def model_to_rpp(discovery: Discovery) -> dict:
    rpp = RPPDiscovery(
        versions=[RPPDiscoveryVersion(version=discovery.version, base_url=discovery.base_url)],
        environment=RPPDiscoveryEnvironment(name=discovery.environment_name, status=discovery.environment_status),
        tlds=discovery.tlds,
        objects=discovery.objects,
        datetime=discovery.datetime,
    ).to_rpp()
    validate_schema("discovery.read", rpp)
    return rpp
