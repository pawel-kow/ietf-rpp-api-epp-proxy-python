from models import Host, HostUpdateChanges
from rpp_schema_validator import validate_schema
from . import host_dns, prov_metadata
from .common import parse_rpp, reject_set
from .dns_records import nameserver_records
from .rpp_models import RPPDnsData, RPPHost, RPPStatus


def add_rpp_status(status: RPPStatus, target: Host | HostUpdateChanges):
    """Adds a status and its reason to what holds them."""
    reject_set(due=status.due)
    target.status.append(status.label)
    if status.reason:
        target.status_reasons[status.label] = status.reason


def rpp_host_to_model(host_rpp: RPPHost) -> Host:
    """The Host of a parsed request, without its status."""
    if host_rpp.provMetadata:
        raise ValueError("Undeclared property: provMetadata")
    addresses = {"ipv4": [], "ipv6": []}
    if host_rpp.dns:
        reject_set(controls=host_rpp.dns.controls)
        for record in host_rpp.dns.records or []:
            address = host_dns.rpp_to_model(host_rpp.hostName, record)
            if address:
                addresses[address[0]].append(address[1])
    return Host(name=host_rpp.hostName, ipv4=addresses["ipv4"] or None, ipv6=addresses["ipv6"] or None)


def rpp_to_model(rpp: dict) -> Host:
    """Converts a create request to a Host."""
    validate_schema("host.create", rpp)
    host_rpp = parse_rpp(RPPHost, rpp)
    reject_set(status=host_rpp.status)
    return rpp_host_to_model(host_rpp)


def _dns_to_rpp(host: Host) -> RPPDnsData | None:
    if not host.ipv4 and not host.ipv6:
        return None
    return RPPDnsData(records=nameserver_records(host.name, host.ipv4, host.ipv6))


def _statuses_to_rpp(host: Host) -> list[RPPStatus]:
    return [
        RPPStatus(at_type="hostStatus", label=label, reason=host.status_reasons.get(label))
        for label in host.status or []
    ]


def model_to_rpp(host: Host) -> dict:
    """Converts a Host to its read representation."""
    host_dict = RPPHost(
        hostName=host.name,
        provMetadata=prov_metadata.model_to_rpp(host),
        status=_statuses_to_rpp(host),
        dns=_dns_to_rpp(host),
    ).to_rpp()
    validate_schema("host.read", host_dict)
    return host_dict
