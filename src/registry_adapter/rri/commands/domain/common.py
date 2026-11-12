"""What the RRI domain commands share: the domain model ↔ RRI XML, for the full state that CREATE, UPDATE and CHHOLDER
send and INFO reads."""
import base64
import ipaddress
from datetime import datetime, timezone
from dataclasses import dataclass, field

from core.model.domain.dns_sec import DnsSec
from core.model.domain.domain_idn import DomainIdn
from core.model.domain.domains import ContactReference, Domain, HostAttr, NS
from core.model.domain.key_data import KeyData
from core.model.domain.zone_record import ZoneRecord
from registry_adapter.rri.statuses import rgp_status, status_labels
from registry_adapter.rri.xml.generated import dnsentry_5_0 as dns
from registry_adapter.rri.xml.generated.contact_5_0 import RoleType
from registry_adapter.rri.xml.generated.domain_5_0 import ContactType, InfoData, StatusType

REGISTRANT = "registrant"

GENERAL_REQUEST = "generalRequest"

ABUSE = "abuse"

# RPP contact label ↔ RRI role. Every holder is a registrant (gap Q1).
ROLES = {REGISTRANT: RoleType.HOLDER, GENERAL_REQUEST: RoleType.GENERALREQUEST, ABUSE: RoleType.ABUSECONTACT}

LABELS = {role: label for label, role in ROLES.items()}

AUTH_INFO1 = "authInfo1"


@dataclass(kw_only=True)
class DomainState:
    """The full state of a domain as RRI writes it: holders, the REQUEST contacts and the DNS data."""
    holders: list[str] = field(default_factory=list)
    general_request: str | None = None
    abuse: str | None = None
    nameservers: list[HostAttr] = field(default_factory=list)
    records: list[ZoneRecord] = field(default_factory=list)
    keys: list[KeyData] = field(default_factory=list)

    def contacts(self) -> list[ContactType]:
        contacts = [ContactType(value=holder, role=RoleType.HOLDER) for holder in self.holders]
        if self.general_request:
            contacts.append(ContactType(value=self.general_request, role=RoleType.GENERALREQUEST))
        if self.abuse:
            contacts.append(ContactType(value=self.abuse, role=RoleType.ABUSECONTACT))
        return contacts

    def dnsentries(self, ace: str) -> list:
        owner = f"{ace}."
        entries = [dns.Ns(owner=owner, rdata=dns.Ns.Rdata(nameserver=host.id, address=list(host.ipv4 or []),
                                                          address_v6=list(host.ipv6 or [])))
                   for host in self.nameservers]
        for record in self.records:
            if record.type == "mx":
                exchange = "." if record.exchange == "." else f"{record.exchange}."
                entries.append(dns.Mx(owner=f"{record.owner}.", rdata=dns.Mx.Rdata(
                    preference=record.preference, exchange=exchange)))
            elif record.type == "aaaa":
                entries.append(dns.Aaaa(owner=f"{record.owner}.", rdata=dns.Aaaa.Rdata(address=record.address)))
            else:
                entries.append(dns.A(owner=f"{record.owner}.", rdata=dns.A.Rdata(address=record.address)))
        entries += [dns.Dnskey(owner=owner, rdata=dns.Dnskey.Rdata(
            flags=key.flags, protocol=key.protocol, algorithm=key.algorithm,
            public_key=base64.b64decode(key.publicKey))) for key in self.keys]
        return entries

    def same_holders(self, other: "DomainState") -> bool:
        return sorted(h.upper() for h in self.holders) == sorted(h.upper() for h in other.holders)

    def key(self):
        """What a comparison of two states looks at, in the form the registry stores."""
        def upper(value):
            return value.upper() if value else value
        return (
            sorted(h.upper() for h in self.holders), upper(self.general_request), upper(self.abuse),
            sorted((h.id.lower(), tuple(sorted(h.ipv4 or [])), tuple(sorted(h.ipv6 or []))) for h in self.nameservers),
            sorted((r.owner.lower(), r.type, r.address or "", r.preference or 0, (r.exchange or "").lower())
                   for r in self.records),
            sorted((k.flags, k.protocol, k.algorithm, k.publicKey.replace(" ", "")) for k in self.keys),
        )


def handle_and_ace(name: str) -> tuple[str, str | None]:
    """The `handle` and `ace` of a domain name: RRI names an IDN by its U-label, with the A-label as `ace`."""
    name = name.lower()
    labels = name.split(".")
    if not any(label.startswith("xn--") for label in labels):
        return name, None
    try:
        u_labels = [label[4:].encode("ascii").decode("punycode") if label.startswith("xn--") else label
                    for label in labels]
    except (UnicodeError, ValueError):
        return name, None
    return ".".join(u_labels), name


def domain_names(name: str) -> dict:
    """The `handle` and `ace` fields of a request on the domain."""
    handle, ace = handle_and_ace(name)
    return {"handle": handle, "ace": ace}


def state_of(domain_name: str, *, registrants: list[str], contacts: list[tuple[str, str]], ns: NS | None,
             records: list[ZoneRecord] | None, dns_sec: DnsSec | None) -> DomainState:
    """The state of a domain from the model: registrants, and the other contacts as (label, id)."""
    state = DomainState(holders=list(registrants))
    for label, contact_id in contacts:
        if label == REGISTRANT:
            state.holders.append(contact_id)
        elif label == GENERAL_REQUEST:
            state.general_request = contact_id
        elif label == ABUSE:
            state.abuse = contact_id
    state.nameservers = list((ns.host_attrs if ns else None) or [])
    state.records = list(records or [])
    state.keys = list((dns_sec.key_data if dns_sec else None) or [])
    return state


def state_of_domain(domain: Domain) -> DomainState:
    contacts = [(label, contact.id) for contact in domain.contacts or [] for label in contact.types]
    return state_of(domain.name, registrants=[], contacts=contacts, ns=domain.ns, records=domain.records,
                    dns_sec=domain.dnsSEC)


def _datetime(value) -> str | None:
    """A date of RRI (ISO 8601 with an offset) in the UTC form the EPP adapter gives too."""
    if value is None:
        return None
    moment = value.to_datetime() if hasattr(value, "to_datetime") else datetime.fromisoformat(value)
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _ip(value: str) -> str:
    """An address in its canonical text form: RRI writes IPv6 addresses uncompressed."""
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return value


def _owner(value: str) -> str:
    return value.lower().removesuffix(".") or "."


def _dns_from_rri(entries, domain_name: str):
    hosts, records, keys = [], [], []
    for entry in entries:
        value = getattr(entry, "value", entry)
        if isinstance(value, dns.Ns):
            hosts.append(HostAttr(id=value.rdata.nameserver.removesuffix("."),
                                  ipv4=[_ip(a) for a in value.rdata.address] or None,
                                  ipv6=[_ip(a) for a in value.rdata.address_v6] or None))
        elif isinstance(value, dns.Mx):
            records.append(ZoneRecord(owner=_owner(value.owner), type="mx", preference=value.rdata.preference,
                                      exchange=_owner(value.rdata.exchange)))
        elif isinstance(value, dns.Aaaa):
            records.append(ZoneRecord(owner=_owner(value.owner), type="aaaa", address=_ip(value.rdata.address)))
        elif isinstance(value, dns.A):
            records.append(ZoneRecord(owner=_owner(value.owner), type="a", address=_ip(value.rdata.address)))
        elif isinstance(value, dns.Dnskey):
            keys.append(KeyData(flags=value.rdata.flags, protocol=value.rdata.protocol,
                                algorithm=value.rdata.algorithm,
                                publicKey=base64.b64encode(value.rdata.public_key).decode("ascii")))
    ns = NS(host_objs=None, host_attrs=hosts) if hosts else None
    return ns, records or None, DnsSec(key_data=keys) if keys else None


def domain_from_rri(data: InfoData, lgr: str | None) -> Domain:
    """A domain from its INFO. The RPP name is the A-label; the U-label is shown where an LGR is configured. A
    registration date given as `before …` is unknown, and RRI never shows an AuthInfo, only when it expires."""
    contacts = [ContactReference(id=contact.handle.value, types=[LABELS[contact.role]])
                for contact in data.contact if contact.role in LABELS and contact.handle is not None]
    # The first registrant is the one RPP shows as `registrant`: holders first.
    contacts.sort(key=lambda contact: contact.types != [REGISTRANT])
    ns, records, dns_sec = _dns_from_rri(data.dnsentry, data.ace or data.handle)
    registration = data.registration_date
    name = (data.ace or data.handle).lower()
    idn = DomainIdn(lgr=lgr, uname=data.handle) if lgr and data.ace and data.handle.lower() != data.ace.lower() else None
    status = status_labels(data.status)
    due = {"inactive": _datetime(data.expire)} if data.status == StatusType.FAILED and data.expire else {}
    return Domain(
        name=name,
        status=status,
        status_due=due,
        rgpStatus=rgp_status(data.status),
        contacts=contacts or None,
        ns=ns,
        records=records,
        dnsSEC=dns_sec,
        idn=idn,
        crDate=_datetime(registration) if registration and not registration.startswith("before") else None,
        upDate=_datetime(data.changed),
        clID=data.reg_acc.reg_acc_id if data.reg_acc else None,
        carried_over={AUTH_INFO1: _datetime(data.auth_info1)} if data.auth_info1 else {},
    )


def has_auth_info1(domain: Domain) -> bool:
    return bool((domain.carried_over or {}).get(AUTH_INFO1))
