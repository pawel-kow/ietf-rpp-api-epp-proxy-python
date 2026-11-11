import jsonschema
import pytest

from core.model.host.host_update import HostUpdate
from core.model.host.host_update_changes import HostUpdateChanges
from core.capabilities.unsupported_feature import UnsupportedFeature
from rpp.mapping.host import host_patch

NAME = "ns1.example.example"
A = {"@type": "dnsRecord", "name": f"{NAME}.", "type": "a", "rdata": {"address": "192.0.2.1"}}
AAAA = {"@type": "dnsRecord", "name": "@", "type": "aaaa", "rdata": {"address": "2001:db8::1"}}
NS = {"@type": "dnsRecord", "name": "@", "type": "ns", "rdata": {"nsdname": f"{NAME}."}}
STATUS = {"@type": "hostStatus", "label": "clientUpdateProhibited"}


def update(*operations):
    return host_patch.rpp_to_model(NAME, list(operations))


def add(path, value):
    return {"op": "add", "path": path, "value": value}


def remove(path, match):
    return {"op": "remove", "path": path, "match": match}


def test_no_operations_changes_nothing():
    assert update() == HostUpdate(name=NAME)


@pytest.mark.parametrize("op", ["add", "replace"])
def test_host_name_change(op):
    assert update({"op": op, "path": "/hostName", "value": "ns2.example.example"}).new_name == "ns2.example.example"


def test_host_name_cannot_be_removed():
    with pytest.raises(UnsupportedFeature):
        update({"op": "remove", "path": "/hostName"})


def test_host_name_change_cannot_use_match():
    with pytest.raises(ValueError):
        update({"op": "replace", "path": "/hostName", "value": "x.example", "match": {"a": 1}})


def test_add_status():
    assert update(add("/status", STATUS)).add == HostUpdateChanges(status=["clientUpdateProhibited"])


def test_add_status_rejects_a_server_status():
    with pytest.raises(jsonschema.ValidationError):
        update(add("/status", {"@type": "hostStatus", "label": "ok"}))


def test_add_status_keeps_the_reason():
    assert update(add("/status", {**STATUS, "reason": "x"})).add == HostUpdateChanges(
        status=["clientUpdateProhibited"], status_reasons={"clientUpdateProhibited": "x"}
    )


def test_remove_status():
    assert update(remove("/status", {"label": "clientUpdateProhibited"})).remove == HostUpdateChanges(
        status=["clientUpdateProhibited"]
    )


@pytest.mark.parametrize("match", [
    {"reason": "x"},
    {"label": "clientUpdateProhibited", "reason": "x"},
    {"label": "linked"},
])
def test_remove_status_with_more_than_a_client_label_needs_the_current_host(match):
    assert update(remove("/status", match)) is None


def test_add_records():
    changes = update(add("/dns/records", A), add("/dns/records", AAAA)).add

    assert changes == HostUpdateChanges(ipv4=["192.0.2.1"], ipv6=["2001:db8::1"])


def test_add_record_for_another_name_is_unsupported():
    with pytest.raises(UnsupportedFeature):
        update(add("/dns/records", {**A, "name": "www"}))


def test_add_own_ns_record_changes_nothing():
    assert update(add("/dns/records", NS)) == HostUpdate(name=NAME)


def test_add_own_ns_record_keeps_the_rest_of_the_patch():
    assert update(add("/dns/records", NS), add("/dns/records", A)).add == HostUpdateChanges(ipv4=["192.0.2.1"])


def test_add_ns_record_of_another_host_is_unsupported():
    with pytest.raises(UnsupportedFeature):
        update(add("/dns/records", {**NS, "rdata": {"nsdname": "ns2.example.example."}}))


def test_remove_record_by_type_and_rdata():
    match = {"type": "a", "rdata": {"address": "192.0.2.1"}}

    assert update(remove("/dns/records", match)).remove == HostUpdateChanges(ipv4=["192.0.2.1"])


def test_remove_record_with_a_full_match():
    assert update(remove("/dns/records", A)).remove == HostUpdateChanges(ipv4=["192.0.2.1"])


@pytest.mark.parametrize("match", [
    {"type": "a"},
    {"rdata": {"address": "192.0.2.1"}},
    {"type": "ns", "rdata": {"nsdname": f"{NAME}."}},
])
def test_remove_record_by_a_partial_match_needs_the_current_host(match):
    assert update(remove("/dns/records", match)) is None


@pytest.mark.parametrize("path", ["/status", "/dns/records"])
def test_add_cannot_use_match(path):
    value = STATUS if path == "/status" else A

    with pytest.raises(ValueError):
        update({"op": "add", "path": path, "value": value, "match": {"label": "x"}})


@pytest.mark.parametrize("operation", [
    {"op": "replace", "path": "/status", "value": []},
    {"op": "replace", "path": "/dns/records", "value": []},
    {"op": "remove", "path": "/status"},
    {"op": "remove", "path": "/dns/records"},
    {"op": "replace", "path": "/status", "match": {"label": "ok"}, "value": STATUS},
    {"op": "replace", "path": "/dns", "value": {"@type": "dnsData"}},
    {"op": "remove", "path": "/dns"},
    {"op": "remove", "path": "/dns/controls"},
])
def test_operations_needing_the_current_host_have_no_direct_update(operation):
    assert update(operation) is None


def test_other_paths_cannot_be_changed():
    with pytest.raises(ValueError):
        update({"op": "replace", "path": "/provMetadata", "value": {}})


def test_other_operations_are_not_allowed():
    with pytest.raises(ValueError):
        update({"op": "move", "path": "/hostName", "value": "x"})
