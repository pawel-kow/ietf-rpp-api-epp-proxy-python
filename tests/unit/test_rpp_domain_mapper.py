from dataclasses import replace

import pytest
from jsonschema import ValidationError

from core.capabilities.unsupported_feature import UnsupportedFeature
from core.model.domain.domain_idn import DomainIdn
from core.model.domain.domains import ContactReference, Domain, HostObj, NS
from core.model.shared.common import AuthInfo
from registry_adapter.epp.profile import EPP_PROFILE
from rpp.mapping.domain import domains

IDN_PROFILE = replace(EPP_PROFILE, lgrs=frozenset({"latn-1.0"}))


def create_body(**extra):
    return {"@type": "domainName", "name": "foo.example", **extra}


def contact(contact_id):
    return {"@type": "contact", "id": contact_id}


def info_domain(**extra):
    return Domain(name="FOO.EXAMPLE", status=["ok"], clID="ClientX", **extra)


def test_create_maps_nameservers_to_host_objects():
    body = create_body(nameservers=[{"@type": "host", "hostName": "ns1.foo.example"}])

    assert domains.rpp_to_model(body, profile=EPP_PROFILE).ns == NS(host_objs=[HostObj(id="ns1.foo.example")], host_attrs=None)


def test_create_maps_registrant_and_labelled_contacts():
    body = create_body(
        registrant=contact("JD-1234"),
        contacts=[{"label": "admin", "object": contact("SH-8013")}],
    )

    assert domains.rpp_to_model(body, profile=EPP_PROFILE).contacts == [
        ContactReference(id="JD-1234", types=["registrant"]),
        ContactReference(id="SH-8013", types=["admin"]),
    ]


def test_create_maps_authinfo_method_to_password():
    body = create_body(authInfo={"@type": "authInfo", "method": "authinfo", "authdata": "2fooBAR"})

    assert domains.rpp_to_model(body, profile=EPP_PROFILE).authInfo == AuthInfo(pw="2fooBAR")


@pytest.mark.parametrize("value, unit, duration", [(2, "y", "P2Y"), (6, "m", "P6M")])
def test_create_maps_period_to_duration(value, unit, duration):
    body = create_body(processes={"@type": "processes", "createProcess": [{
        "@type": "domainCreateProcess",
        "period": {"@type": "period", "value": value, "unit": unit},
    }]})

    assert domains.rpp_to_model(body, profile=EPP_PROFILE).processes["creation"].duration == duration


@pytest.mark.parametrize("extra", [
    {"status": [{"@type": "domainStatus", "label": "clientHold"}]},
    {"authInfo": {"@type": "authInfo", "method": "other", "authdata": "x"}},
    {"contacts": [{"label": "reseller", "object": {"@type": "contact", "id": "X"}}]},
])
def test_create_rejects_what_the_model_cannot_hold(extra):
    with pytest.raises(UnsupportedFeature):
        domains.rpp_to_model(create_body(**extra), profile=EPP_PROFILE)


def test_create_rejects_a_schema_violation():
    with pytest.raises(ValidationError):
        domains.rpp_to_model({"name": "foo.example"}, profile=EPP_PROFILE)


def test_create_rejects_undeclared_properties():
    with pytest.raises(ValueError):
        domains.rpp_to_model(create_body(unknown="x"), profile=EPP_PROFILE)


def test_read_builds_provisioning_metadata():
    rpp = domains.model_to_rpp(info_domain(
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
    rpp = domains.model_to_rpp(info_domain(exDate="2027-01-01T00:00:00.000000Z"))

    assert rpp["expiryDate"] == "2027-01-01T00:00:00.000000Z"
    assert rpp["status"] == [{"@type": "domainStatus", "label": "ok"}]


def test_read_splits_registrant_from_labelled_contacts():
    rpp = domains.model_to_rpp(info_domain(contacts=[
        ContactReference(id="A", types=["admin", "registrant"]),
        ContactReference(id="B", types=["tech"]),
    ]))

    assert rpp["registrant"] == contact("A")
    assert rpp["contacts"] == [
        {"label": "admin", "object": contact("A")},
        {"label": "tech", "object": contact("B")},
    ]


def test_read_maps_host_objects_to_host_references():
    rpp = domains.model_to_rpp(info_domain(ns=NS(host_objs=[HostObj(id="ns1.foo.example")], host_attrs=None)))

    assert rpp["nameservers"] == [{"@type": "host", "hostName": "ns1.foo.example"}]


def test_read_maps_password_to_authinfo():
    rpp = domains.model_to_rpp(info_domain(authInfo=AuthInfo(pw="2fooBAR")))

    assert rpp["authInfo"] == {"@type": "authInfo", "method": "authinfo", "authdata": "2fooBAR"}


def test_read_leaves_out_unset_members():
    assert set(domains.model_to_rpp(info_domain())) == {"@type", "name", "provMetadata", "status"}


def test_read_builds_repository_and_update_client():
    metadata = domains.model_to_rpp(info_domain(roid="D1-EX", upID="ClientY"))["provMetadata"]

    assert metadata["repositoryId"] == "D1-EX"
    assert metadata["upClientId"] == "ClientY"


def test_read_has_the_status_reason():
    domain = Domain(name="foo.example", roid="D1", status=["clientHold", "ok"], status_reasons={"clientHold": "Unpaid"},
                    crDate="2026-11-04T10:00:00Z", clID="foo", crID="foo")

    assert domains.model_to_rpp(domain)["status"] == [
        {"@type": "domainStatus", "label": "clientHold", "reason": "Unpaid"},
        {"@type": "domainStatus", "label": "ok"},
    ]


def idn_body(**extra):
    return create_body(name="xn--bcher-kva.example", **extra)


def test_create_keeps_lgr_and_uname():
    domain = domains.rpp_to_model(idn_body(uName="bücher.example", lgr="latn-1.0"), profile=IDN_PROFILE)

    assert domain.idn == DomainIdn(lgr="latn-1.0", uname="bücher.example")


def test_create_keeps_lgr_alone():
    assert domains.rpp_to_model(idn_body(lgr="latn-1.0"), profile=IDN_PROFILE).idn == DomainIdn(lgr="latn-1.0")


def test_create_without_lgr_has_no_idn():
    assert domains.rpp_to_model(idn_body(), profile=IDN_PROFILE).idn is None


def test_create_with_uname_and_no_lgr_is_refused():
    """Json §6.4: lgr MUST be present whenever uName is present."""
    with pytest.raises(ValueError) as refused:
        domains.rpp_to_model(idn_body(uName="bücher.example"), profile=IDN_PROFILE)

    assert not isinstance(refused.value, UnsupportedFeature)


@pytest.mark.parametrize("profile", [IDN_PROFILE, EPP_PROFILE])
def test_create_with_an_lgr_the_backend_does_not_offer_is_refused(profile):
    with pytest.raises(ValueError) as refused:
        domains.rpp_to_model(idn_body(lgr="cyrl-1.0"), profile=profile)

    assert not isinstance(refused.value, UnsupportedFeature)


def test_create_on_a_backend_without_lgrs_refuses_any_lgr():
    with pytest.raises(ValueError):
        domains.rpp_to_model(idn_body(lgr="latn-1.0"), profile=EPP_PROFILE)


def test_read_has_lgr_and_uname():
    rpp = domains.model_to_rpp(info_domain(idn=DomainIdn(lgr="latn-1.0", uname="bücher.example")))

    assert rpp["uName"] == "bücher.example"
    assert rpp["lgr"] == "latn-1.0"


def test_read_has_lgr_alone():
    rpp = domains.model_to_rpp(info_domain(idn=DomainIdn(lgr="latn-1.0")))

    assert rpp["lgr"] == "latn-1.0"
    assert "uName" not in rpp


def test_read_without_idn_has_no_uname_or_lgr():
    rpp = domains.model_to_rpp(info_domain())

    assert "uName" not in rpp
    assert "lgr" not in rpp
