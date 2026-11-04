import jsonschema
import pytest

from models import Host, HostCheckResponse, ResultCode
from rpp_to_model_mapper import (
    UnsupportedRppFeature, host_availability_to_rpp, host_to_rpp, rpp_to_host, rpp_to_host_replacement,
)

NAME = "ns1.example.example"


def record(record_type, rdata, name=f"{NAME}."):
    return {"@type": "dnsRecord", "name": name, "type": record_type, "rdata": rdata}


def host(*records, **members):
    body = {"@type": "host", "hostName": NAME, **members}
    if records:
        body["dns"] = {"@type": "dnsData", "records": list(records)}
    return body


A = record("a", {"address": "192.0.2.1"})
AAAA = record("aaaa", {"address": "2001:db8::1"})
NS = record("ns", {"nsdname": f"{NAME}."}, name="@")


def test_host_without_dns_has_no_addresses():
    assert rpp_to_host(host()) == Host(name=NAME)


def test_a_and_aaaa_records_become_addresses():
    mapped = rpp_to_host(host(NS, A, AAAA))

    assert mapped.ipv4 == ["192.0.2.1"]
    assert mapped.ipv6 == ["2001:db8::1"]


@pytest.mark.parametrize("name", ["@", NAME, f"{NAME}.", f"{NAME.upper()}."])
def test_a_record_may_name_the_host_itself(name):
    assert rpp_to_host(host(record("a", {"address": "192.0.2.1"}, name=name))).ipv4 == ["192.0.2.1"]


@pytest.mark.parametrize("name", ["www", f"sub.{NAME}.", "ns2.example.example."])
def test_a_record_for_another_name_is_unsupported(name):
    with pytest.raises(UnsupportedRppFeature):
        rpp_to_host(host(record("a", {"address": "192.0.2.1"}, name=name)))


@pytest.mark.parametrize("nsdname", [NAME, f"{NAME}.", f"{NAME.upper()}."])
def test_self_referencing_ns_record_adds_nothing(nsdname):
    assert rpp_to_host(host(record("ns", {"nsdname": nsdname}, name="@"))) == Host(name=NAME)


def test_ns_record_for_another_host_is_unsupported():
    with pytest.raises(UnsupportedRppFeature):
        rpp_to_host(host(record("ns", {"nsdname": "ns2.example.example."}, name="@")))


def test_ns_record_at_another_name_is_unsupported():
    with pytest.raises(UnsupportedRppFeature):
        rpp_to_host(host(record("ns", {"nsdname": f"{NAME}."}, name="other.example.")))


def test_other_record_types_are_unsupported():
    with pytest.raises(UnsupportedRppFeature):
        rpp_to_host(host(record("txt", {"text": "x"})))


def test_class_in_is_accepted():
    assert rpp_to_host(host({**A, "class": "IN"})).ipv4 == ["192.0.2.1"]


def test_other_classes_are_unsupported():
    with pytest.raises(UnsupportedRppFeature):
        rpp_to_host(host({**A, "class": "CH"}))


@pytest.mark.parametrize("bad", [
    record("a", {"address": "2001:db8::1"}),
    record("aaaa", {"address": "192.0.2.1"}),
    record("a", {"address": "not-an-ip"}),
    record("a", {}),
    record("a", {"address": "192.0.2.1", "extra": 1}),
    record("ns", {}),
])
def test_invalid_rdata_is_a_client_error(bad):
    with pytest.raises(ValueError):
        rpp_to_host(host(bad))


def test_dns_controls_are_unsupported():
    body = host(A)
    body["dns"]["controls"] = {"@type": "dnsControls", "ttl": {"a": 3600}}

    with pytest.raises(UnsupportedRppFeature):
        rpp_to_host(body)


def test_status_on_create_is_unsupported():
    with pytest.raises(UnsupportedRppFeature):
        rpp_to_host(host(status=[{"@type": "hostStatus", "label": "clientUpdateProhibited"}]))


def test_undeclared_property_is_rejected():
    with pytest.raises(ValueError):
        rpp_to_host(host(unknown=1))


def test_request_is_validated_against_the_schema():
    with pytest.raises(jsonschema.ValidationError):
        rpp_to_host({"@type": "host"})


def test_replacement_keeps_status_labels():
    body = host(A, status=[{"@type": "hostStatus", "label": "clientDeleteProhibited"}])

    assert rpp_to_host_replacement(body).status == ["clientDeleteProhibited"]


def test_replacement_keeps_a_status_reason():
    body = host(status=[{"@type": "hostStatus", "label": "clientDeleteProhibited", "reason": "x"}])

    assert rpp_to_host_replacement(body).status_reasons == {"clientDeleteProhibited": "x"}


def test_replacement_rejects_dns_controls():
    body = host(A)
    body["dns"]["controls"] = {"@type": "dnsControls", "ttl": {"a": 3600}}

    with pytest.raises(UnsupportedRppFeature):
        rpp_to_host_replacement(body)


def stored(**members):
    return Host(name="NS1.EXAMPLE.EXAMPLE", status=["ok"], clID="ClientX", crID="ClientY",
                crDate="1999-04-03T22:00:00.000000Z", **members)


def test_read_representation_follows_the_draft_example():
    rpp = host_to_rpp(stored(ipv4=["192.0.2.1"], ipv6=["2001:db8::1"]))

    assert rpp["@type"] == "host"
    assert rpp["hostName"] == "NS1.EXAMPLE.EXAMPLE"
    assert rpp["status"] == [{"@type": "hostStatus", "label": "ok"}]
    assert rpp["provMetadata"]["spClientId"] == "ClientX"
    assert rpp["dns"]["@type"] == "dnsData"
    assert rpp["dns"]["records"] == [
        {"@type": "dnsRecord", "name": "@", "type": "ns", "rdata": {"nsdname": "NS1.EXAMPLE.EXAMPLE."}},
        {"@type": "dnsRecord", "name": "NS1.EXAMPLE.EXAMPLE.", "type": "a", "rdata": {"address": "192.0.2.1"}},
        {"@type": "dnsRecord", "name": "NS1.EXAMPLE.EXAMPLE.", "type": "aaaa", "rdata": {"address": "2001:db8::1"}},
    ]


def test_read_gives_a_status_reason():
    rpp = host_to_rpp(Host(name=NAME, status=["clientDeleteProhibited"], status_reasons={"clientDeleteProhibited": "x"},
                           clID="ClientX"))

    assert rpp["status"] == [{"@type": "hostStatus", "label": "clientDeleteProhibited", "reason": "x"}]


def test_host_without_addresses_has_no_dns():
    assert "dns" not in host_to_rpp(stored())


def availability(available, reason=None):
    return HostCheckResponse(
        host_name=NAME, available=available, reason=reason, code=ResultCode.COMMAND_COMPLETED_SUCCESSFULLY,
        msg="ok", server_transaction_id="sv", client_transaction_id=None,
    )


def test_available_host():
    assert host_availability_to_rpp(availability(True)) == {"@type": "hostAvailability", "available": True}


def test_taken_host_gives_the_reason():
    assert host_availability_to_rpp(availability(False, "In use")) == {
        "@type": "hostAvailability", "available": False, "reason": "In use",
    }
