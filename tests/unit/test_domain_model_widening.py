"""What the domain model holds beyond EPP, for a backend whose profile says so: records the registry serves itself,
several registrants and the deadline of a status. The EPP profile still refuses them."""

import pytest

from core.capabilities.not_supported_by_backend import NotSupportedByBackend
from core.model.domain import domain_application, domain_difference
from core.model.domain.domains import ContactReference, Domain, DomainUpdate, HostAttr
from core.model.domain.zone_record import ZoneRecord
from tests.helper.profiles import EPP_PROFILE
from rpp.mapping.domain import domain_patch, domain_wanted, domains

OTHER = EPP_PROFILE.with_changes({"name": "Other", "domainName": {
    "registrant": {"max_count": 5}, "contacts": {"labels": ["generalRequest", "abuse"]},
    "dns": {"record_types": ["ns", "a", "aaaa", "mx", "dnskey"]}}})


def record(name, record_type, rdata):
    return {"@type": "dnsRecord", "name": name, "type": record_type, "rdata": rdata}


def create(*records, profile=OTHER, **extra):
    return domains.rpp_to_model({
        "@type": "domainName", "name": "foo.example",
        **({"dns": {"@type": "dnsData", "records": list(records)}} if records else {}), **extra,
    }, profile=profile)


def test_address_and_mail_records_are_zone_records():
    domain = create(
        record("@", "a", {"address": "192.0.2.1"}),
        record("www", "aaaa", {"address": "2001:db8::1"}),
        record("@", "mx", {"preference": "10", "exchange": "mx.foo.example."}),
    )

    assert domain.records == [
        ZoneRecord(owner="foo.example", type="mx", preference=10, exchange="mx.foo.example"),
        ZoneRecord(owner="foo.example", type="a", address="192.0.2.1"),
        ZoneRecord(owner="www.foo.example", type="aaaa", address="2001:db8::1"),
    ]
    assert domain.ns is None


def test_an_address_of_a_nameserver_of_the_domain_stays_glue():
    domain = create(record("@", "ns", {"nsdname": "ns1.foo.example."}),
                    record("ns1.foo.example.", "a", {"address": "192.0.2.1"}))

    assert domain.ns.host_attrs == [HostAttr(id="ns1.foo.example", ipv4=["192.0.2.1"])]
    assert domain.records == None


def test_epp_still_refuses_records_it_does_not_serve():
    with pytest.raises(NotSupportedByBackend, match="A DNS record for '@'"):
        create(record("@", "a", {"address": "192.0.2.1"}), profile=EPP_PROFILE)
    with pytest.raises(NotSupportedByBackend, match="DNS record type 'mx'"):
        create(record("@", "mx", {"preference": "10", "exchange": "mx.foo.example."}), profile=EPP_PROFILE)


def test_a_record_outside_the_domain_is_refused():
    with pytest.raises(NotSupportedByBackend):
        create(record("other.example.", "a", {"address": "192.0.2.1"}))


def test_zone_records_are_read_back_as_records():
    domain = Domain(name="foo.example", clID="foo", status=["ok"], records=[
        ZoneRecord(owner="foo.example", type="a", address="192.0.2.1"),
        ZoneRecord(owner="www.foo.example", type="mx", preference=0, exchange="."),
    ])

    assert domains.model_to_rpp(domain)["dns"]["records"] == [
        record("@", "a", {"address": "192.0.2.1"}),
        record("www.foo.example.", "mx", {"preference": "0", "exchange": "."}),
    ]


REGISTRANTS = {
    "registrant": {"@type": "contact", "id": "H1"},
    "contacts": [{"label": "registrant", "object": {"@type": "contact", "id": "H2"}},
                 {"label": "abuse", "object": {"@type": "contact", "id": "AB"}}],
}


def test_further_registrants_are_contacts_labelled_registrant():
    domain = create(**REGISTRANTS)
    domain.clID, domain.status = "foo", ["ok"]

    assert domain.contacts == [ContactReference(id="H1", types=["registrant"]),
                               ContactReference(id="H2", types=["registrant"]),
                               ContactReference(id="AB", types=["abuse"])]
    rpp = domains.model_to_rpp(domain)
    assert rpp["registrant"]["id"] == "H1"
    assert [(c["label"], c["object"]["id"]) for c in rpp["contacts"]] == [("registrant", "H2"), ("abuse", "AB")]


def test_epp_refuses_a_second_registrant():
    with pytest.raises(NotSupportedByBackend, match="Contact label 'registrant'"):
        create(profile=OTHER.with_changes({"domainName": {"registrant": {"max_count": 1}}}), **REGISTRANTS)


def test_more_registrants_than_the_backend_holds_are_refused():
    with pytest.raises(NotSupportedByBackend, match="More than 1 registrants"):
        domain_wanted.rpp_to_model("foo.example", REGISTRANTS, None, frozenset(),
                                   profile=OTHER.with_changes({"domainName": {
                                       "registrant": {"max_count": 1}, "contacts": {"labels": ["abuse", "registrant"]}}}))


def test_full_update_keeps_further_registrants_and_records():
    wanted = domain_wanted.rpp_to_model("foo.example", {
        **REGISTRANTS, "dns": {"@type": "dnsData", "records": [record("@", "a", {"address": "192.0.2.1"})]},
    }, None, frozenset(), profile=OTHER)

    assert wanted.registrant == "H1"
    assert [(c.type, c.contact.id) for c in wanted.contacts] == [("registrant", "H2"), ("abuse", "AB")]
    assert wanted.records == [ZoneRecord(owner="foo.example", type="a", address="192.0.2.1")]


def test_patch_of_a_further_registrant_needs_the_current_domain():
    add = [{"op": "add", "path": "/contacts", "value": REGISTRANTS["contacts"][0]}]
    remove = [{"op": "remove", "path": "/contacts", "match": REGISTRANTS["contacts"][0]}]

    assert domain_patch.rpp_to_model("foo.example", add, profile=OTHER) is None
    assert domain_patch.rpp_to_model("foo.example", remove, profile=OTHER) is None


def test_applying_a_delta_keeps_records_and_further_registrants():
    current = Domain(name="foo.example", contacts=[ContactReference(id="H1", types=["registrant"]),
                                                   ContactReference(id="H2", types=["registrant"])],
                     records=[ZoneRecord(owner="foo.example", type="a", address="192.0.2.1")])

    wanted = domain_application.apply(current, DomainUpdate(name="foo.example"))

    assert wanted.registrant == "H1"
    assert [(c.type, c.contact.id) for c in wanted.contacts] == [("registrant", "H2")]
    assert wanted.records == current.records
    assert domain_difference.contacts_of(current)[0].contact.id == "H2"


def test_status_due_is_shown():
    domain = Domain(name="foo.example", clID="foo", status=["inactive"], status_due={"inactive": "2026-12-01T10:00:00Z"})

    assert domains.model_to_rpp(domain)["status"] == [
        {"@type": "domainStatus", "label": "inactive", "due": "2026-12-01T10:00:00Z"}]
