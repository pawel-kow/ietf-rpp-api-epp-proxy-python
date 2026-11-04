import jsonschema
import pytest

from models import HostUpdate, HostUpdateChanges
from rpp_to_model_mapper import UnsupportedRppFeature, rpp_to_host_update

NAME = "ns1.example.example"
A = {"@type": "dnsRecord", "name": f"{NAME}.", "type": "a", "rdata": {"address": "192.0.2.1"}}
AAAA = {"@type": "dnsRecord", "name": "@", "type": "aaaa", "rdata": {"address": "2001:db8::1"}}
STATUS = {"@type": "hostStatus", "label": "clientUpdateProhibited"}


def update(*operations):
    return rpp_to_host_update(NAME, list(operations))


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
    with pytest.raises(UnsupportedRppFeature):
        update({"op": "remove", "path": "/hostName"})


def test_host_name_change_cannot_use_match():
    with pytest.raises(ValueError):
        update({"op": "replace", "path": "/hostName", "value": "x.example", "match": {"a": 1}})


def test_add_status():
    assert update(add("/status", STATUS)).add == HostUpdateChanges(status=["clientUpdateProhibited"])


def test_add_status_rejects_a_server_status():
    with pytest.raises(jsonschema.ValidationError):
        update(add("/status", {"@type": "hostStatus", "label": "ok"}))


def test_add_status_rejects_a_reason():
    with pytest.raises(UnsupportedRppFeature):
        update(add("/status", {**STATUS, "reason": "x"}))


def test_remove_status():
    assert update(remove("/status", {"label": "clientUpdateProhibited"})).remove == HostUpdateChanges(
        status=["clientUpdateProhibited"]
    )


def test_remove_status_needs_the_label():
    with pytest.raises(UnsupportedRppFeature):
        update(remove("/status", {"reason": "x"}))


def test_add_records():
    changes = update(add("/dns/records", A), add("/dns/records", AAAA)).add

    assert changes == HostUpdateChanges(ipv4=["192.0.2.1"], ipv6=["2001:db8::1"])


def test_add_record_for_another_name_is_unsupported():
    with pytest.raises(UnsupportedRppFeature):
        update(add("/dns/records", {**A, "name": "www"}))


def test_add_ns_record_is_unsupported():
    ns = {"@type": "dnsRecord", "name": "@", "type": "ns", "rdata": {"nsdname": f"{NAME}."}}

    with pytest.raises(UnsupportedRppFeature):
        update(add("/dns/records", ns))


def test_remove_record_by_type_and_rdata():
    match = {"type": "a", "rdata": {"address": "192.0.2.1"}}

    assert update(remove("/dns/records", match)).remove == HostUpdateChanges(ipv4=["192.0.2.1"])


def test_remove_record_with_a_full_match():
    assert update(remove("/dns/records", A)).remove == HostUpdateChanges(ipv4=["192.0.2.1"])


@pytest.mark.parametrize("match", [{"type": "a"}, {"rdata": {"address": "192.0.2.1"}}])
def test_remove_record_needs_type_and_rdata(match):
    with pytest.raises(UnsupportedRppFeature):
        update(remove("/dns/records", match))


@pytest.mark.parametrize("path", ["/status", "/dns/records"])
def test_add_cannot_use_match(path):
    value = STATUS if path == "/status" else A

    with pytest.raises(ValueError):
        update({"op": "add", "path": path, "value": value, "match": {"label": "x"}})


@pytest.mark.parametrize("path", ["/status", "/dns/records"])
def test_replace_needs_the_current_object(path):
    with pytest.raises(UnsupportedRppFeature):
        update({"op": "replace", "path": path, "value": []})


@pytest.mark.parametrize("path", ["/status", "/dns/records"])
def test_remove_without_match_needs_the_current_object(path):
    with pytest.raises(UnsupportedRppFeature):
        update({"op": "remove", "path": path})


@pytest.mark.parametrize("path", ["/dns", "/dns/controls"])
def test_dns_as_a_whole_is_unsupported(path):
    with pytest.raises(UnsupportedRppFeature):
        update({"op": "replace", "path": path, "value": {}})


def test_other_paths_cannot_be_changed():
    with pytest.raises(ValueError):
        update({"op": "replace", "path": "/provMetadata", "value": {}})


def test_other_operations_are_not_allowed():
    with pytest.raises(ValueError):
        update({"op": "move", "path": "/hostName", "value": "x"})
