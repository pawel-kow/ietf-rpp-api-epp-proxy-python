from eppclient.epp_profile import EPP_PROFILE
import pytest
from jsonschema import ValidationError

from models import AuthInfo, ContactMinimal, ContactReferenceNew, HostObj
from rpp_to_model_mapper import UnsupportedRppFeature, domain_patch

CONTACT = {"@type": "contact", "id": "SH-8014"}
HOST = {"@type": "host", "hostName": "ns1.foo.example"}
AUTH = {"@type": "authInfo", "method": "authinfo", "authdata": "2BARfoo"}


def update(*operations):
    return domain_patch.rpp_to_model("foo.example", list(operations), profile=EPP_PROFILE)


def reference(label):
    return ContactReferenceNew(type=label, contact=ContactMinimal(id="SH-8014"))


def test_add_nameserver():
    result = update({"op": "add", "path": "/nameservers", "value": HOST})

    assert result.add.ns.host_objs == [HostObj(id="ns1.foo.example")]


def test_remove_nameserver_by_match():
    result = update({"op": "remove", "path": "/nameservers", "match": {"hostName": "ns1.foo.example"}})

    assert result.remove.ns.host_objs == [HostObj(id="ns1.foo.example")]


def test_add_contact():
    result = update({"op": "add", "path": "/contacts", "value": {"label": "tech", "object": CONTACT}})

    assert result.add.contacts == [reference("tech")]


def test_remove_contact_by_match():
    result = update({"op": "remove", "path": "/contacts", "match": {"label": "tech", "object": CONTACT}})

    assert result.remove.contacts == [reference("tech")]


@pytest.mark.parametrize("op", ["add", "replace"])
def test_set_registrant(op):
    result = update({"op": op, "path": "/registrant", "value": CONTACT})

    assert result.add.contacts == [reference("registrant")]


def test_remove_registrant_clears_it():
    result = update({"op": "remove", "path": "/registrant"})

    assert [c.type for c in result.remove.contacts] == ["registrant"]


def test_replace_authinfo():
    result = update({"op": "replace", "path": "/authInfo", "value": AUTH})

    assert result.change.authInfo == AuthInfo(pw="2BARfoo")


def test_operations_accumulate():
    result = update(
        {"op": "add", "path": "/nameservers", "value": HOST},
        {"op": "replace", "path": "/authInfo", "value": AUTH},
    )

    assert result.name == "foo.example"
    assert result.add.ns and result.change.authInfo
    assert result.remove is None


@pytest.mark.parametrize("operation", [
    {"op": "replace", "path": "/nameservers", "value": [HOST]},
    {"op": "replace", "path": "/contacts", "value": []},
    {"op": "remove", "path": "/nameservers"},
    {"op": "remove", "path": "/contacts", "match": {"label": "tech"}},
    {"op": "replace", "path": "/nameservers", "match": {"hostName": "a"}, "value": HOST},
    {"op": "replace", "path": "/status", "match": {"label": "ok"}, "value": {"@type": "domainStatus", "label": "clientHold"}},
    {"op": "replace", "path": "/dns", "value": {"@type": "dnsData"}},
    {"op": "replace", "path": "/dns/records", "value": []},
    {"op": "add", "path": "/dns/records", "value": {}},
    {"op": "remove", "path": "/dns/records", "match": {"type": "ds"}},
    {"op": "remove", "path": "/dns/controls"},
])
def test_operations_needing_the_current_domain_have_no_direct_update(operation):
    assert update(operation) is None


def test_remove_auth_info_clears_it():
    assert update({"op": "remove", "path": "/authInfo"}).change.clear_auth_info is True


@pytest.mark.parametrize("operation", [
    {"op": "replace", "path": "/name", "value": "bar.example"},
    {"op": "replace", "path": "/unknown", "value": "x"},
    {"op": "add", "path": "/nameservers", "match": {"hostName": "a"}, "value": HOST},
    {"op": "replace", "path": "/registrant", "match": {"id": "a"}, "value": CONTACT},
    {"op": "move", "path": "/registrant", "value": CONTACT},
])
def test_invalid_operations_are_rejected(operation):
    with pytest.raises(ValueError):
        update(operation)


@pytest.mark.parametrize("operation", [
    {"op": "add", "path": "/nameservers", "value": {"hostName": "no-type"}},
    {"op": "add", "path": "/contacts", "value": {"label": "tech"}},
    {"op": "replace", "path": "/registrant", "value": {"id": "no-type"}},
    {"op": "replace", "path": "/authInfo", "value": {"pw": "old"}},
])
def test_values_are_validated_against_the_schema(operation):
    with pytest.raises(ValidationError):
        update(operation)


def test_unknown_contact_label_is_unsupported():
    with pytest.raises(UnsupportedRppFeature):
        update({"op": "add", "path": "/contacts", "value": {"label": "reseller", "object": CONTACT}})
