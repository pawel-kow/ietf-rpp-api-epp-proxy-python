import pytest
from jsonschema import ValidationError

from models import (
    AuthInfo, ContactReference, Domain, HostAttr, HostObj, NS,
)
from rpp_to_model_mapper import UnsupportedRppFeature, domain_to_rpp, rpp_to_domain


def create_body(**extra):
    return {"@type": "domainName", "name": "foo.example", **extra}


def contact(contact_id):
    return {"@type": "contact", "id": contact_id}


def info_domain(**extra):
    return Domain(name="FOO.EXAMPLE", status=["ok"], clID="ClientX", **extra)


def test_create_maps_nameservers_to_host_objects():
    body = create_body(nameservers=[{"@type": "host", "hostName": "ns1.foo.example"}])

    assert rpp_to_domain(body).ns == NS(host_objs=[HostObj(id="ns1.foo.example")], host_attrs=None)


def test_create_maps_registrant_and_labelled_contacts():
    body = create_body(
        registrant=contact("JD-1234"),
        contacts=[{"label": "admin", "object": contact("SH-8013")}],
    )

    assert rpp_to_domain(body).contacts == [
        ContactReference(id="JD-1234", types=["registrant"]),
        ContactReference(id="SH-8013", types=["admin"]),
    ]


def test_create_maps_authinfo_method_to_password():
    body = create_body(authInfo={"@type": "authInfo", "method": "authinfo", "authdata": "2fooBAR"})

    assert rpp_to_domain(body).authInfo == AuthInfo(pw="2fooBAR")


@pytest.mark.parametrize("value, unit, duration", [(2, "y", "P2Y"), (6, "m", "P6M")])
def test_create_maps_period_to_duration(value, unit, duration):
    body = create_body(processes={"@type": "processes", "createProcess": [{
        "@type": "domainCreateProcess",
        "period": {"@type": "period", "value": value, "unit": unit},
    }]})

    assert rpp_to_domain(body).processes["creation"].duration == duration


@pytest.mark.parametrize("extra", [
    {"dns": {"@type": "dnsData"}},
    {"status": [{"@type": "domainStatus", "label": "clientHold"}]},
    {"uName": "bücher.example"},
    {"lgr": "latn-1.0"},
    {"authInfo": {"@type": "authInfo", "method": "other", "authdata": "x"}},
    {"contacts": [{"label": "reseller", "object": {"@type": "contact", "id": "X"}}]},
])
def test_create_rejects_what_the_model_cannot_hold(extra):
    with pytest.raises(UnsupportedRppFeature):
        rpp_to_domain(create_body(**extra))


def test_create_rejects_a_schema_violation():
    with pytest.raises(ValidationError):
        rpp_to_domain({"name": "foo.example"})


def test_create_rejects_undeclared_properties():
    with pytest.raises(ValueError):
        rpp_to_domain(create_body(unknown="x"))


def test_read_builds_provisioning_metadata():
    rpp = domain_to_rpp(info_domain(
        crID="ClientY", crDate="2026-01-01T00:00:00.000000Z",
        upDate="2026-01-02T00:00:00.000000Z", trDate="2026-01-03T00:00:00.000000Z",
    ))

    assert rpp["provMetadata"] == {
        "@type": "provMetadata",
        "spClientId": "ClientX",
        "crClientId": "ClientY",
        "crDate": "2026-01-01T00:00:00.000000Z",
        "upDate": "2026-01-02T00:00:00.000000Z",
        "trDate": "2026-01-03T00:00:00.000000Z",
    }


def test_read_maps_expiry_and_status_objects():
    rpp = domain_to_rpp(info_domain(exDate="2027-01-01T00:00:00.000000Z"))

    assert rpp["expiryDate"] == "2027-01-01T00:00:00.000000Z"
    assert rpp["status"] == [{"@type": "domainStatus", "label": "ok"}]


def test_read_splits_registrant_from_labelled_contacts():
    rpp = domain_to_rpp(info_domain(contacts=[
        ContactReference(id="A", types=["admin", "registrant"]),
        ContactReference(id="B", types=["tech"]),
    ]))

    assert rpp["registrant"] == contact("A")
    assert rpp["contacts"] == [
        {"label": "admin", "object": contact("A")},
        {"label": "tech", "object": contact("B")},
    ]


def test_read_maps_host_objects_and_attributes_to_host_references():
    rpp = domain_to_rpp(info_domain(ns=NS(
        host_objs=[HostObj(id="ns1.foo.example")],
        host_attrs=[HostAttr(id="ns2.foo.example", ipv4=["192.0.2.1"])],
    )))

    assert rpp["nameservers"] == [
        {"@type": "host", "hostName": "ns1.foo.example"},
        {"@type": "host", "hostName": "ns2.foo.example"},
    ]


def test_read_maps_password_to_authinfo():
    rpp = domain_to_rpp(info_domain(authInfo=AuthInfo(pw="2fooBAR")))

    assert rpp["authInfo"] == {"@type": "authInfo", "method": "authinfo", "authdata": "2fooBAR"}


def test_read_leaves_out_unset_members():
    assert set(domain_to_rpp(info_domain())) == {"@type", "name", "provMetadata", "status"}
