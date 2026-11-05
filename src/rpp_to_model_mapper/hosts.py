from models import Host, HostCheckResponse, HostUpdateChanges
from rpp_schema_validator import validate_schema
from .common import parse_rpp, prov_metadata_to_rpp, reject_set
from .dns_records import (
    ADDRESS_RECORDS, ORIGIN, check_record_class, nameserver_records, record_address, record_rdata, record_type,
)
from .rpp_models import RPPDnsData, RPPDnsRecord, RPPHost, RPPHostAvailability, RPPStatus
from .unsupported_rpp_feature import UnsupportedRppFeature


def _is_host(host_name: str, name: str) -> bool:
    return name.removesuffix(".").lower() == host_name.lower()


def rpp_record_to_address(host_name: str, record: RPPDnsRecord) -> tuple[str, str] | None:
    """The address family and address of a record. EPP holds only the glue of the host itself.

    The self-referencing `ns` record carries nothing EPP has to hold, so it gives None.
    """
    check_record_class(record)
    if record.name != ORIGIN and not _is_host(host_name, record.name):
        raise UnsupportedRppFeature(f"A DNS record for '{record.name}' is not supported")
    kind = record_type(record)
    if kind == "ns":
        if not _is_host(host_name, record_rdata(record, "nsdname")[0]):
            raise UnsupportedRppFeature("An 'ns' record for another host is not supported")
        return None
    if kind not in ADDRESS_RECORDS:
        raise UnsupportedRppFeature(f"DNS record type '{record.type}' is not supported")
    return record_address(record)


def add_rpp_status(status: RPPStatus, target: Host | HostUpdateChanges):
    """Adds a status and its reason to what holds them."""
    reject_set(due=status.due)
    target.status.append(status.label)
    if status.reason:
        target.status_reasons[status.label] = status.reason


def _rpp_to_host(host_rpp: RPPHost) -> Host:
    if host_rpp.provMetadata:
        raise ValueError("Undeclared property: provMetadata")
    addresses = {"ipv4": [], "ipv6": []}
    if host_rpp.dns:
        reject_set(controls=host_rpp.dns.controls)
        for record in host_rpp.dns.records or []:
            address = rpp_record_to_address(host_rpp.hostName, record)
            if address:
                addresses[address[0]].append(address[1])
    return Host(name=host_rpp.hostName, ipv4=addresses["ipv4"] or None, ipv6=addresses["ipv6"] or None)


def rpp_to_host(rpp: dict) -> Host:
    """Converts a create request to a Host."""
    validate_schema("host.create", rpp)
    host_rpp = parse_rpp(RPPHost, rpp)
    reject_set(status=host_rpp.status)
    return _rpp_to_host(host_rpp)


def rpp_to_host_replacement(rpp: dict) -> Host:
    """Converts a full update to the Host it asks for."""
    validate_schema("host.update", rpp)
    host_rpp = parse_rpp(RPPHost, rpp)
    host = _rpp_to_host(host_rpp)
    host.status = []
    for status in host_rpp.status or []:
        add_rpp_status(status, host)
    return host


def _dns_to_rpp(host: Host) -> RPPDnsData | None:
    if not host.ipv4 and not host.ipv6:
        return None
    return RPPDnsData(records=nameserver_records(host.name, host.ipv4, host.ipv6))


def _statuses_to_rpp(host: Host) -> list[RPPStatus]:
    return [
        RPPStatus(at_type="hostStatus", label=label, reason=host.status_reasons.get(label))
        for label in host.status or []
    ]


def host_to_rpp(host: Host) -> dict:
    """Converts a Host to its read representation."""
    host_dict = RPPHost(
        hostName=host.name,
        provMetadata=prov_metadata_to_rpp(host),
        status=_statuses_to_rpp(host),
        dns=_dns_to_rpp(host),
    ).to_rpp()
    validate_schema("host.read", host_dict)
    return host_dict


def host_availability_to_rpp(check: HostCheckResponse) -> dict:
    availability = RPPHostAvailability(available=check.available, reason=check.reason).to_rpp()
    validate_schema("hostAvailability.read", availability)
    return availability
