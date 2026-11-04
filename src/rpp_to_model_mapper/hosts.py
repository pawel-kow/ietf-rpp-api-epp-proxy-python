import ipaddress

from models import Host, HostCheckResponse, HostUpdateChanges
from rpp_schema_validator import validate_schema
from .common import parse_rpp, prov_metadata_to_rpp, reject_set
from .rpp_models import RPPDnsData, RPPDnsRecord, RPPHost, RPPHostAvailability, RPPStatus
from .unsupported_rpp_feature import UnsupportedRppFeature

ADDRESS_RECORDS = {"a": ("ipv4", ipaddress.IPv4Address), "aaaa": ("ipv6", ipaddress.IPv6Address)}
ORIGIN = "@"
RECORD_CLASS_INTERNET = "IN"


def _is_host(host_name: str, name: str) -> bool:
    return name.removesuffix(".").lower() == host_name.lower()


def _rdata(record: RPPDnsRecord, member: str):
    if set(record.rdata) != {member}:
        raise ValueError(f"The rdata of a '{record.type}' record must have '{member}' only")
    return record.rdata[member]


def _check_address(record: RPPDnsRecord, address_class) -> str:
    address = _rdata(record, "address")
    if not isinstance(address, str):
        raise ValueError("The address of a record must be a string")
    address_class(address)  # raises a ValueError
    return address


def rpp_record_to_address(host_name: str, record: RPPDnsRecord) -> tuple[str, str] | None:
    """The address family and address of a record. EPP holds only the glue of the host itself.

    The self-referencing `ns` record carries nothing EPP has to hold, so it gives None.
    """
    if record.record_class not in (None, RECORD_CLASS_INTERNET):
        raise UnsupportedRppFeature(f"DNS class '{record.record_class}' is not supported")
    if record.name != ORIGIN and not _is_host(host_name, record.name):
        raise UnsupportedRppFeature(f"A DNS record for '{record.name}' is not supported")
    if record.type == "ns":
        if not _is_host(host_name, str(_rdata(record, "nsdname"))):
            raise UnsupportedRppFeature("An 'ns' record for another host is not supported")
        return None
    if record.type not in ADDRESS_RECORDS:
        raise UnsupportedRppFeature(f"DNS record type '{record.type}' is not supported")
    family, address_class = ADDRESS_RECORDS[record.type]
    return family, _check_address(record, address_class)


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
    fqdn = f"{host.name}."
    records = [RPPDnsRecord(name=ORIGIN, type="ns", rdata={"nsdname": fqdn})]
    records += [RPPDnsRecord(name=fqdn, type="a", rdata={"address": ip}) for ip in host.ipv4 or []]
    records += [RPPDnsRecord(name=fqdn, type="aaaa", rdata={"address": ip}) for ip in host.ipv6 or []]
    return RPPDnsData(records=records)


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
