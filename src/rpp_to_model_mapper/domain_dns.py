import base64
import re

from models import DnsSec, Domain, DsData, HostAttr, KeyData, NS
from .dns_records import (
    ADDRESS_RECORDS, ORIGIN, check_record_class, nameserver_records, record_address, record_rdata, record_type,
    reject_ttl,
)
from .not_supported_by_epp import NotSupportedByEpp
from .not_supported_by_proxy import NotSupportedByProxy
from .rpp_models import RPPDnsData, RPPDnsRecord

HEX = re.compile(r"(?:[0-9A-Fa-f]{2})+")
MAX_BYTE = 255
MAX_SHORT = 65535
ZONE_APEX_RECORDS = ("ns", "ds", "dnskey")


def _number(value: str, maximum: int) -> int:
    if not (value.isascii() and value.isdigit()) or int(value) > maximum:
        raise ValueError(f"'{value}' is not a number up to {maximum}")
    return int(value)


def _rpp_to_ds(record: RPPDnsRecord) -> DsData:
    key_tag, algorithm, digest_type, digest = record_rdata(record, "keyTag", "algorithm", "digestType", "digest")
    if HEX.fullmatch(digest) is None:
        raise ValueError("The digest of a 'ds' record must be hexadecimal")
    return DsData(
        keyTag=_number(key_tag, MAX_SHORT),
        algorithm=_number(algorithm, MAX_BYTE),
        digestType=_number(digest_type, MAX_BYTE),
        digest=digest.upper(),
    )


def _rpp_to_key(record: RPPDnsRecord) -> KeyData:
    flags, protocol, algorithm, public_key = record_rdata(record, "flags", "protocol", "algorithm", "publicKey")
    if not base64.b64decode(public_key, validate=True):  # raises a ValueError
        raise ValueError("The public key of a 'dnskey' record is empty")
    return KeyData(
        flags=_number(flags, MAX_SHORT),
        protocol=_number(protocol, MAX_BYTE),
        algorithm=_number(algorithm, MAX_BYTE),
        publicKey=public_key,
    )


def _owner(domain_name: str, name: str) -> str:
    """The owner as an absolute name without the dot, in lowercase.

    A name that ends in the domain counts as absolute even without the dot, as it does for hosts.
    """
    name = name.lower()
    if name == ORIGIN:
        return domain_name
    if name.endswith("."):
        return name.removesuffix(".")
    if name == domain_name or name.endswith(f".{domain_name}"):
        return name
    return f"{name}.{domain_name}"


def _add_glue(hosts: dict[str, HostAttr], owner: str, record: RPPDnsRecord):
    """EPP holds addresses only on a nameserver of the domain. Whether the nameserver may have them is the
    registry's to decide: what a read can show must be accepted as input."""
    family, address = record_address(record)
    if owner not in hosts:
        raise NotSupportedByEpp(f"A DNS record for '{record.name}'")
    host = hosts[owner]
    setattr(host, family, (getattr(host, family) or []) + [address])


def _reject_controls(controls: dict | None):
    """secDNS has `maxSigLife`, which the proxy does not map."""
    if controls:
        reject_ttl(controls)
        raise NotSupportedByProxy("'dns.controls'")


def rpp_to_model(domain_name: str, dns: RPPDnsData) -> tuple[NS | None, DnsSec | None]:
    """The delegation and DNSSEC data of the records. Delegation goes to EPP as host attributes."""
    _reject_controls(dns.controls)
    domain_name = domain_name.lower()
    hosts: dict[str, HostAttr] = {}
    ds_data, key_data, glue = [], [], []
    for record in dns.records or []:
        check_record_class(record)
        kind = record_type(record)
        owner = _owner(domain_name, record.name)
        if kind in ADDRESS_RECORDS:
            glue.append((owner, record))
        elif kind not in ZONE_APEX_RECORDS:
            raise NotSupportedByEpp(f"DNS record type '{record.type}'")
        elif owner != domain_name:
            raise NotSupportedByEpp(f"A DNS record for '{record.name}'")
        elif kind == "ns":
            host_name = record_rdata(record, "nsdname")[0].removesuffix(".")
            hosts.setdefault(host_name.lower(), HostAttr(id=host_name))
        elif kind == "ds":
            ds_data.append(_rpp_to_ds(record))
        else:
            key_data.append(_rpp_to_key(record))
    if ds_data and key_data:
        raise NotSupportedByProxy("'ds' and 'dnskey' records in one request")
    for owner, record in glue:
        _add_glue(hosts, owner, record)
    ns = NS(host_objs=None, host_attrs=list(hosts.values())) if hosts else None
    dns_sec = DnsSec(ds_data=ds_data or None, key_data=key_data or None) if ds_data or key_data else None
    return ns, dns_sec


def _ds_to_rpp(ds: DsData) -> RPPDnsRecord:
    return RPPDnsRecord(name=ORIGIN, type="ds", rdata={
        "keyTag": str(ds.keyTag),
        "algorithm": str(ds.algorithm),
        "digestType": str(ds.digestType),
        "digest": ds.digest,
    })


def _key_to_rpp(key: KeyData) -> RPPDnsRecord:
    return RPPDnsRecord(name=ORIGIN, type="dnskey", rdata={
        "flags": str(key.flags),
        "protocol": str(key.protocol),
        "algorithm": str(key.algorithm),
        "publicKey": key.publicKey,
    })


def model_to_rpp(domain: Domain) -> RPPDnsData | None:
    """Host attributes and DNSSEC data as records. Host objects are `nameservers`."""
    records = []
    for host in (domain.ns.host_attrs if domain.ns else None) or []:
        records += nameserver_records(host.id, host.ipv4, host.ipv6)
    if domain.dnsSEC:
        records += [_ds_to_rpp(ds) for ds in domain.dnsSEC.ds_data or []]
        records += [_key_to_rpp(key) for key in domain.dnsSEC.key_data or []]
    return RPPDnsData(records=records) if records else None
