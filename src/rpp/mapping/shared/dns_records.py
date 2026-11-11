import ipaddress

from core.capabilities.not_supported_by_backend import NotSupportedByBackend
from core.capabilities.not_supported_by_proxy import NotSupportedByProxy
from rpp.dto.rpp_dns_record import RPPDnsRecord

ADDRESS_RECORDS = {"a": ("ipv4", ipaddress.IPv4Address), "aaaa": ("ipv6", ipaddress.IPv6Address)}
ORIGIN = "@"
RECORD_CLASS_INTERNET = "IN"
TTL_EXTENSION = "RFC 9803"
# For JSON Patch: the object an operation on a member of `dns` starts from when the object has no `dns`.
DNS_PARENTS = {"/dns": {"@type": "dnsData"}}


def record_type(record: RPPDnsRecord) -> str:
    """The type in lowercase, as the data objects draft (§9.9) requires."""
    return record.type.lower()


def check_record_class(record: RPPDnsRecord):
    if record.record_class not in (None, RECORD_CLASS_INTERNET):
        raise NotSupportedByBackend(f"DNS class '{record.record_class}'")


def reject_ttl(controls: dict):
    if "ttl" in controls:
        raise NotSupportedByProxy("'dns.controls.ttl'", TTL_EXTENSION)


def record_rdata(record: RPPDnsRecord, *members: str) -> list[str]:
    """The values of the rdata, which has the given members only and holds strings (json draft §6.2.4)."""
    if set(record.rdata) != set(members):
        raise ValueError(f"The rdata of a '{record.type}' record must have {', '.join(members)} only")
    values = [record.rdata[member] for member in members]
    if not all(isinstance(value, str) for value in values):
        raise ValueError(f"The rdata values of a '{record.type}' record must be strings")
    return values


def record_address(record: RPPDnsRecord) -> tuple[str, str]:
    """The address family and address of an A or AAAA record."""
    family, address_class = ADDRESS_RECORDS[record_type(record)]
    address = record_rdata(record, "address")[0]
    address_class(address)  # raises a ValueError
    return family, address


def nameserver_records(host_name: str, ipv4: list[str] | None, ipv6: list[str] | None) -> list[RPPDnsRecord]:
    """The `ns` record of a nameserver and the records of its addresses."""
    fqdn = f"{host_name}."
    records = [RPPDnsRecord(name=ORIGIN, type="ns", rdata={"nsdname": fqdn})]
    records += [RPPDnsRecord(name=fqdn, type="a", rdata={"address": ip}) for ip in ipv4 or []]
    records += [RPPDnsRecord(name=fqdn, type="aaaa", rdata={"address": ip}) for ip in ipv6 or []]
    return records
