import pytest

from core.capabilities.unsupported_feature import UnsupportedFeature
from core.model.domain.dns_sec import DnsSec
from core.model.domain.domains import Domain, HostAttr, HostObj, NS
from core.model.domain.ds_data import DsData
from core.model.domain.key_data import KeyData
from tests.helper.profiles import EPP_PROFILE
from rpp.mapping.domain import domains

DS_RDATA = {"keyTag": "12345", "algorithm": "3", "digestType": "1", "digest": "49FD46E6C4B45C55D4AC"}

KEY_RDATA = {"flags": "257", "protocol": "3", "algorithm": "8", "publicKey": "AQPJ////4Q=="}

DS = DsData(keyTag=12345, algorithm=3, digestType=1, digest="49FD46E6C4B45C55D4AC")

KEY = KeyData(flags=257, protocol=3, algorithm=8, publicKey="AQPJ////4Q==")


def record(name, record_type, rdata, **extra):
    return {"@type": "dnsRecord", "name": name, "type": record_type, "rdata": rdata, **extra}


def ns(host="ns1.foo.example."):
    return record("@", "ns", {"nsdname": host})


def glue(name="ns1.foo.example.", record_type="a", address="192.0.2.1"):
    return record(name, record_type, {"address": address})


def create(*records, **extra):
    return domains.rpp_to_model({
        "@type": "domainName",
        "name": "foo.example",
        "dns": {"@type": "dnsData", "records": list(records), **extra},
    }, profile=EPP_PROFILE)


def read(**extra):
    return domains.model_to_rpp(Domain(name="foo.example", status=["ok"], clID="ClientX", **extra))


def test_create_without_records_holds_nothing():
    domain = create()

    assert domain.ns is None
    assert domain.dnsSEC is None


def test_create_maps_a_ds_record():
    assert create(record("@", "ds", DS_RDATA)).dnsSEC == DnsSec(ds_data=[DS])


def test_create_maps_a_dnskey_record():
    assert create(record("foo.example.", "dnskey", KEY_RDATA)).dnsSEC == DnsSec(key_data=[KEY])


def test_create_converts_the_record_type_to_lowercase():
    assert create(record("@", "DS", DS_RDATA)).dnsSEC == DnsSec(ds_data=[DS])


def test_create_maps_an_ns_record_without_glue_to_a_host_attribute():
    assert create(ns()).ns == NS(host_objs=None, host_attrs=[HostAttr(id="ns1.foo.example")])


def test_create_adds_glue_to_the_nameserver():
    domain = create(glue(), glue(record_type="aaaa", address="2001:db8::1"), ns())

    assert domain.ns.host_attrs == [HostAttr(id="ns1.foo.example", ipv4=["192.0.2.1"], ipv6=["2001:db8::1"])]


def test_create_takes_a_relative_owner_name():
    assert create(ns(), glue("ns1")).ns.host_attrs[0].ipv4 == ["192.0.2.1"]


def test_create_keeps_a_nameserver_of_another_domain():
    assert create(ns("ns1.other.example.")).ns.host_attrs == [HostAttr(id="ns1.other.example")]


def test_create_leaves_glue_of_another_domain_to_the_registry():
    """A read shows what the registry stores, so the same records are accepted as input."""
    domain = create(ns("ns1.other.example."), glue("ns1.other.example."))

    assert domain.ns.host_attrs == [HostAttr(id="ns1.other.example", ipv4=["192.0.2.1"])]


def test_create_can_hold_delegation_and_dnssec_together():
    domain = create(ns(), record("@", "ds", DS_RDATA))

    assert domain.ns.host_attrs == [HostAttr(id="ns1.foo.example")]
    assert domain.dnsSEC == DnsSec(ds_data=[DS])


def test_create_rejects_dns_records_together_with_nameservers():
    with pytest.raises(ValueError):
        domains.rpp_to_model({
            "@type": "domainName",
            "name": "foo.example",
            "nameservers": [{"@type": "host", "hostName": "ns1.foo.example"}],
            "dns": {"@type": "dnsData", "records": [ns()]},
        }, profile=EPP_PROFILE)


@pytest.mark.parametrize("records", [
    [record("@", "ds", {**DS_RDATA, "keyTag": 12345})],
    [record("@", "ds", {**DS_RDATA, "keyTag": "65536"})],
    [record("@", "ds", {**DS_RDATA, "algorithm": "x"})],
    [record("@", "ds", {**DS_RDATA, "digest": "XY"})],
    [record("@", "ds", {**DS_RDATA, "digest": "ABC"})],
    [record("@", "ds", {**DS_RDATA, "extra": "1"})],
    [record("@", "dnskey", {**KEY_RDATA, "publicKey": "not base64!"})],
    [record("@", "dnskey", {**KEY_RDATA, "flags": "65536"})],
    [record("@", "dnskey", {k: v for k, v in KEY_RDATA.items() if k != "protocol"})],
    [ns(), glue(address="192.0.2.300")],
    [ns(), glue(record_type="aaaa")],
])
def test_create_rejects_what_the_draft_forbids(records):
    with pytest.raises(ValueError):
        create(*records)


@pytest.mark.parametrize("records", [
    [record("@", "ds", DS_RDATA), record("@", "dnskey", KEY_RDATA)],
    [record("sub", "ds", DS_RDATA)],
    [record("sub", "dnskey", KEY_RDATA)],
    [record("sub", "ns", {"nsdname": "ns1.foo.example."})],
    [glue("@")],
    [glue()],
    [record("@", "mx", {"exchange": "mail.foo.example."})],
    [record("@", "ds", DS_RDATA, **{"class": "CH"})],
])
def test_create_rejects_what_epp_cannot_hold(records):
    with pytest.raises(UnsupportedFeature):
        create(*records)


def test_create_rejects_dns_controls():
    with pytest.raises(UnsupportedFeature):
        create(controls={"@type": "dnsControls", "ttl": {"ds": 3600}})


def test_read_maps_host_attributes_to_dns_records():
    rpp = read(ns=NS(host_objs=None, host_attrs=[
        HostAttr(id="ns1.foo.example", ipv4=["192.0.2.1"], ipv6=["2001:db8::1"]),
    ]))

    assert "nameservers" not in rpp
    assert rpp["dns"] == {"@type": "dnsData", "records": [
        ns(),
        glue(),
        glue(record_type="aaaa", address="2001:db8::1"),
    ]}


def test_read_maps_dnssec_to_dns_records():
    assert read(dnsSEC=DnsSec(ds_data=[DS], key_data=[KEY]))["dns"]["records"] == [
        record("@", "ds", DS_RDATA),
        record("@", "dnskey", KEY_RDATA),
    ]


def test_read_keeps_host_objects_in_nameservers_next_to_dnssec():
    rpp = read(ns=NS(host_objs=[HostObj(id="ns1.foo.example")], host_attrs=None), dnsSEC=DnsSec(ds_data=[DS]))

    assert rpp["nameservers"] == [{"@type": "host", "hostName": "ns1.foo.example"}]
    assert rpp["dns"]["records"] == [record("@", "ds", DS_RDATA)]


def test_read_leaves_out_dns_without_records():
    assert "dns" not in read(ns=NS(host_objs=[HostObj(id="ns1.foo.example")], host_attrs=None))


def test_read_maps_subordinate_hosts():
    assert read(subordinateHosts=["ns1.foo.example"])["subordinateHosts"] == [
        {"@type": "host", "hostName": "ns1.foo.example"},
    ]
