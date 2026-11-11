from models import Host, HostReplacement, HostUpdateChanges
from rpp_schema_validator import validate_schema
from . import host_dns, prov_metadata
from .common import parse_rpp, reject_set
from .dns_records import nameserver_records, reject_ttl
from .not_supported_by_backend import NotSupportedByBackend
from .rpp_models import RPPDnsData, RPPHost, RPPStatus


def add_rpp_status(status: RPPStatus, target: Host | HostUpdateChanges):
    """Adds a status and its reason to what holds them."""
    reject_set(due=status.due)
    target.status.append(status.label)
    if status.reason:
        target.status_reasons[status.label] = status.reason


def _reject_controls(controls: dict | None):
    """EPP has a TTL extension for hosts, but `maxSigLifetime` is secDNS, which is for domains only."""
    if controls:
        reject_ttl(controls)
        raise NotSupportedByBackend("'dns.controls' on a host")


def has_own_ns(host_rpp: RPPHost) -> bool:
    """Whether the host has its self-referencing `ns` record, which `host_dns` maps to nothing."""
    records = host_rpp.dns.records if host_rpp.dns else None
    return any(host_dns.rpp_to_model(host_rpp.hostName, record) is None for record in records or [])


def require_own_ns(host_rpp: RPPHost):
    """A request has to state the `ns` record every read gives, see spec-issues.md."""
    if not has_own_ns(host_rpp):
        raise ValueError(f"The 'ns' record of '{host_rpp.hostName}' is required")


def rpp_host_to_model(host_rpp: RPPHost) -> Host:
    """The Host of a parsed request, without its status."""
    if host_rpp.provMetadata:
        raise ValueError("Undeclared property: provMetadata")
    addresses = {"ipv4": [], "ipv6": []}
    if host_rpp.dns:
        _reject_controls(host_rpp.dns.controls)
        for record in host_rpp.dns.records or []:
            address = host_dns.rpp_to_model(host_rpp.hostName, record)
            if address:
                addresses[address[0]].append(address[1])
    return Host(name=host_rpp.hostName, ipv4=addresses["ipv4"] or None, ipv6=addresses["ipv6"] or None)


def replacement_from_rpp(host_name: str, host_rpp: RPPHost) -> HostReplacement:
    """The host a full update or a patched read asks for. `host_name` is the name the host has now."""
    host = rpp_host_to_model(host_rpp)
    host.status = []
    for status in host_rpp.status or []:
        add_rpp_status(status, host)
    return HostReplacement(
        name=host_name, new_name=host.name, ipv4=host.ipv4, ipv6=host.ipv6,
        status=host.status, status_reasons=host.status_reasons,
    )


def rpp_to_model(rpp: dict) -> Host:
    """Converts a create request to a Host."""
    validate_schema("host.create", rpp)
    host_rpp = parse_rpp(RPPHost, rpp)
    reject_set(status=host_rpp.status)
    host = rpp_host_to_model(host_rpp)
    require_own_ns(host_rpp)
    return host


def _dns_to_rpp(host: Host) -> RPPDnsData:
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
