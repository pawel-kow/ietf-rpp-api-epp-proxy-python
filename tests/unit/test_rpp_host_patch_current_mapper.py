import jsonschema
import pytest

from models import Host
from rpp_to_model_mapper import NotSupportedByEpp, NotSupportedByProxy, PatchNotApplicable, host_patch, hosts

NAME = "ns1.foo.example"
RECORD_A = {"@type": "dnsRecord", "name": "@", "type": "a", "rdata": {"address": "198.51.100.1"}}
STATUS = {"@type": "hostStatus", "label": "clientUpdateProhibited"}


def current(**members):
    host = Host(
        name=NAME, roid="H1", status=["ok"], crDate="2026-11-04T10:00:00Z", clID="foo", crID="foo",
        ipv4=["192.0.2.1", "192.0.2.2"], ipv6=["2001:db8::1"],
    )
    for member, value in members.items():
        setattr(host, member, value)
    return hosts.model_to_rpp(host)


def wanted(*operations, **members):
    return host_patch.rpp_to_model_with_current(NAME, list(operations), current(**members))


def op(name, path, **members):
    return {"op": name, "path": path, **members}


def client_statuses(host):
    return [label for label in host.status if label.startswith("client")]


def test_replace_records_gives_the_new_addresses():
    host = wanted(op("replace", "/dns/records", value=[RECORD_A]))

    assert host.ipv4 == ["198.51.100.1"]
    assert host.ipv6 is None


def test_remove_records_gives_no_addresses():
    host = wanted(op("remove", "/dns/records"))

    assert host.ipv4 is None and host.ipv6 is None


def test_remove_dns_gives_no_addresses():
    host = wanted(op("remove", "/dns"))

    assert host.ipv4 is None and host.ipv6 is None


def test_replace_dns():
    host = wanted(op("replace", "/dns", value={"@type": "dnsData", "records": [RECORD_A]}))

    assert host.ipv4 == ["198.51.100.1"]


def test_remove_by_partial_match_removes_every_match():
    host = wanted(op("remove", "/dns/records", match={"type": "a"}))

    assert host.ipv4 is None
    assert host.ipv6 == ["2001:db8::1"]


def test_replace_with_match():
    host = wanted(op("replace", "/dns/records", match={"type": "aaaa"}, value=RECORD_A))

    assert host.ipv4 == ["192.0.2.1", "192.0.2.2", "198.51.100.1"]
    assert host.ipv6 is None


def test_replace_of_records_on_a_host_without_dns():
    host = wanted(op("replace", "/dns/records", value=[RECORD_A]), ipv4=None, ipv6=None)

    assert host.ipv4 == ["198.51.100.1"]


def test_add_after_an_operation_that_reads():
    host = wanted(op("remove", "/status"), op("add", "/dns/records", value=RECORD_A), ipv4=None, ipv6=None)

    assert host.ipv4 == ["198.51.100.1"]


def test_operations_apply_in_order():
    host = wanted(op("remove", "/dns/records"), op("add", "/status", value=STATUS))

    assert client_statuses(host) == ["clientUpdateProhibited"]
    assert host.ipv4 is None


def test_rename_keeps_the_records_of_the_old_name():
    host = wanted(op("replace", "/hostName", value="ns2.foo.example"), op("remove", "/dns/records", match={"type": "aaaa"}))

    assert host.name == "ns2.foo.example"
    assert host.ipv4 == ["192.0.2.1", "192.0.2.2"]


def test_no_element_matches():
    with pytest.raises(PatchNotApplicable, match="Operation 1"):
        wanted(op("remove", "/status", match={"label": "clientDeleteProhibited"}))


def test_ambiguous_replace():
    with pytest.raises(PatchNotApplicable, match="ambiguous"):
        wanted(op("replace", "/dns/records", match={"type": "a"}, value=RECORD_A))


def test_match_on_the_reason_is_compared():
    host = current(status=["clientUpdateProhibited"], status_reasons={"clientUpdateProhibited": "a"})

    with pytest.raises(PatchNotApplicable):
        host_patch.rpp_to_model_with_current(
            NAME, [op("remove", "/status", match={"label": "clientUpdateProhibited", "reason": "b"})], host,
        )


@pytest.mark.parametrize("operation", [op("replace", "/status", value=[]), op("remove", "/status")])
def test_clearing_status_clears_the_client_ones(operation):
    host = wanted(operation, status=["clientUpdateProhibited", "linked"])

    assert client_statuses(host) == []


@pytest.mark.parametrize("operation", [op("replace", "/status", value=[]), op("remove", "/status")])
def test_clearing_status_of_a_host_with_only_ok(operation):
    assert client_statuses(wanted(operation)) == []


def test_replace_status_leaves_the_server_ones_alone():
    host = wanted(op("replace", "/status", value=[STATUS]), status=["clientDeleteProhibited", "linked"])

    assert client_statuses(host) == ["clientUpdateProhibited"]


def test_replace_ok_by_match():
    host = wanted(op("replace", "/status", match={"label": "ok"}, value=STATUS))

    assert client_statuses(host) == ["clientUpdateProhibited"]


@pytest.mark.parametrize("status", [["ok"], ["linked"]])
def test_a_server_status_cannot_be_set(status):
    linked = {"@type": "hostStatus", "label": "linked"}

    with pytest.raises(ValueError, match="linked"):
        wanted(op("replace", "/status", value=[linked]), status=status)


def test_a_server_status_matches_nothing():
    with pytest.raises(PatchNotApplicable):
        wanted(op("remove", "/status", match={"label": "linked"}), status=["linked"])


def test_a_new_reason_is_kept():
    host = wanted(op("replace", "/status", value=[{**STATUS, "reason": "x"}]))

    assert host.status_reasons == {"clientUpdateProhibited": "x"}


def test_ttl_in_controls_is_for_the_proxy():
    with pytest.raises(NotSupportedByProxy):
        wanted(op("replace", "/dns/controls", value={"@type": "dnsControls", "ttl": {"a": 3600}}))


def test_other_controls_are_for_epp():
    with pytest.raises(NotSupportedByEpp):
        wanted(op("replace", "/dns/controls", value={"@type": "dnsControls", "maxSigLifetime": {"ds": 3600}}))


def test_removing_controls_that_are_not_there_fails():
    with pytest.raises(PatchNotApplicable):
        wanted(op("remove", "/dns/controls"))


def test_a_record_epp_cannot_hold():
    with pytest.raises(NotSupportedByEpp):
        wanted(op("remove", "/status"), op("add", "/dns/records", value={**RECORD_A, "name": "www"}))


def test_a_bad_address_is_rejected():
    with pytest.raises(ValueError):
        wanted(op("replace", "/dns/records", value=[{**RECORD_A, "rdata": {"address": "x"}}]))


def test_a_record_that_is_no_record_is_rejected():
    with pytest.raises(jsonschema.ValidationError):
        wanted(op("replace", "/dns/records", value=["x"]))


@pytest.mark.parametrize("path", ["/provMetadata", "/unknown", "/dns/records/0"])
def test_other_paths_cannot_be_changed(path):
    with pytest.raises(ValueError, match="cannot be changed"):
        wanted(op("remove", "/status"), op("replace", path, value={}))


def test_host_name_cannot_be_removed():
    with pytest.raises(NotSupportedByEpp):
        wanted(op("remove", "/status"), op("remove", "/hostName"))
