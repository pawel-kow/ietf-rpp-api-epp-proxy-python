import jsonschema
import pytest
from connexion import ProblemException

from controller.helper.rpp_response import map_request
from models import ContactReference, Domain, DsData, DnsSec, HostAttr, HostObj, NS
from rpp_to_model_mapper import NotSupportedByEpp, NotSupportedByProxy, PatchNotApplicable, domain_patch, domains

NAME = "foo.example"
HOST = {"@type": "host", "hostName": "ns3.foo.example"}
STATUS = {"@type": "domainStatus", "label": "clientHold"}


def current(**members):
    domain = Domain(
        name=NAME, roid="D1", status=["ok"], crDate="2026-11-04T10:00:00Z", clID="foo", crID="foo",
        ns=NS(host_objs=[HostObj(id="ns1.foo.example"), HostObj(id="ns2.foo.example")], host_attrs=None),
        contacts=[
            ContactReference(id="REG-1", types=["registrant"]),
            ContactReference(id="REG-200", types=["tech"]),
            ContactReference(id="REG-300", types=["tech"]),
        ],
    )
    for member, value in members.items():
        setattr(domain, member, value)
    return domains.model_to_rpp(domain)


def update(*operations, **members):
    return domain_patch.rpp_to_model_with_current(NAME, list(operations), current(**members))


def op(name, path, **members):
    return {"op": name, "path": path, **members}


def host_ids(ns):
    return [host.id for host in ns.host_objs]


def test_replace_whole_nameservers_removes_the_old_and_adds_the_new():
    result = update(op("replace", "/nameservers", value=[HOST]))

    assert host_ids(result.add.ns) == ["ns3.foo.example"]
    assert host_ids(result.remove.ns) == ["ns1.foo.example", "ns2.foo.example"]


def test_replace_keeps_what_is_in_both():
    result = update(op("replace", "/nameservers", value=[{**HOST, "hostName": "NS1.foo.example"}, HOST]))

    assert host_ids(result.add.ns) == ["ns3.foo.example"]
    assert host_ids(result.remove.ns) == ["ns2.foo.example"]


def test_remove_whole_nameservers():
    result = update(op("remove", "/nameservers"))

    assert result.add is None
    assert host_ids(result.remove.ns) == ["ns1.foo.example", "ns2.foo.example"]


def test_remove_contacts_by_partial_match_expands_to_role_and_id():
    result = update(op("remove", "/contacts", match={"label": "tech"}))

    assert [(c.type, c.contact.id) for c in result.remove.contacts] == [("tech", "REG-200"), ("tech", "REG-300")]


def test_replace_contact_by_match():
    value = {"label": "admin", "object": {"@type": "contact", "id": "REG-9"}}

    result = update(op("replace", "/contacts", match={"object": {"id": "REG-300"}}, value=value))

    assert [(c.type, c.contact.id) for c in result.add.contacts] == [("admin", "REG-9")]
    assert [(c.type, c.contact.id) for c in result.remove.contacts] == [("tech", "REG-300")]


def test_replace_registrant():
    result = update(op("replace", "/registrant", value={"@type": "contact", "id": "REG-2"}))

    assert [(c.type, c.contact.id) for c in result.add.contacts] == [("registrant", "REG-2")]
    assert result.remove is None


def test_a_patch_that_changes_nothing_has_an_empty_update():
    result = update(op("replace", "/nameservers", value=[{"@type": "host", "hostName": "ns1.foo.example"}, {"@type": "host", "hostName": "ns2.foo.example"}]))

    assert result.add is None and result.remove is None and result.change is None


def test_add_a_client_status():
    result = update(op("add", "/status", value={**STATUS, "reason": "Pending"}))

    assert result.add.status == ["clientHold"]
    assert result.add.status_reasons == {"clientHold": "Pending"}


def test_replace_status_keeps_the_ones_of_the_server():
    result = update(op("replace", "/status", value=[STATUS]), status=["ok", "clientUpdateProhibited", "serverHold"])

    assert result.add.status == ["clientHold"]
    assert result.remove.status == ["clientUpdateProhibited"]


def test_server_status_cannot_be_set():
    with pytest.raises(ValueError, match="serverHold"):
        update(op("add", "/status", value={"@type": "domainStatus", "label": "serverHold"}))


@pytest.mark.parametrize("operation", [op("replace", "/status", value=[]), op("remove", "/status")])
def test_clearing_status_removes_the_client_ones_only(operation):
    result = update(operation, status=["clientHold", "clientUpdateProhibited", "serverHold"])

    assert result.remove.status == ["clientHold", "clientUpdateProhibited"]
    assert result.add is None


@pytest.mark.parametrize("operation", [op("replace", "/status", value=[]), op("remove", "/status")])
def test_clearing_status_without_client_ones_changes_nothing(operation):
    result = update(operation, status=["ok"])

    assert result.add is None and result.remove is None


def test_a_server_status_cannot_be_named_even_if_the_domain_has_it():
    server_hold = {"@type": "domainStatus", "label": "serverHold"}

    with pytest.raises(ValueError, match="serverHold"):
        update(op("replace", "/status", value=[server_hold]), status=["serverHold"])


def test_a_server_status_matches_nothing():
    with pytest.raises(PatchNotApplicable):
        update(op("remove", "/status", match={"label": "serverHold"}), status=["serverHold"])


def test_replacing_ok_stays_possible():
    assert update(op("replace", "/status", match={"label": "ok"}, value=STATUS)).add.status == ["clientHold"]


def test_a_status_that_is_no_object_is_rejected():
    with pytest.raises(jsonschema.ValidationError):
        update(op("add", "/status", value="clientHold"))


def test_records_can_be_added_to_a_domain_without_dns():
    ds = {"@type": "dnsRecord", "name": "@", "type": "ds", "rdata": {
        "keyTag": "1", "algorithm": "8", "digestType": "2", "digest": "AB",
    }}

    assert update(op("add", "/dns/records", value=ds)).add.dnsSEC.ds_data == [
        DsData(keyTag=1, algorithm=8, digestType=2, digest="AB")
    ]


def test_replace_records_of_a_domain_without_dns_changes_nothing():
    result = update(op("replace", "/dns/records", value=[]))

    assert result.add is None and result.remove is None


def test_ttl_in_dns_controls_is_not_supported():
    with pytest.raises(NotSupportedByProxy):
        update(op("replace", "/dns/controls", value={"@type": "dnsControls", "ttl": {"a": 3600}}))


def test_remove_status_by_match():
    result = update(op("remove", "/status", match={"label": "clientHold"}), status=["ok", "clientHold"])

    assert result.remove.status == ["clientHold"]


def test_status_that_is_not_there_is_not_found():
    with pytest.raises(PatchNotApplicable):
        update(op("remove", "/status", match={"label": "clientHold"}))


def test_dns_records_add_ds_and_host_attributes():
    dns = {"@type": "dnsData", "records": [
        {"@type": "dnsRecord", "name": "@", "type": "ds",
         "rdata": {"keyTag": "1", "algorithm": "8", "digestType": "2", "digest": "ab"}},
    ]}
    result = update(op("replace", "/dns", value=dns))

    assert result.add.dnsSEC.ds_data == [DsData(keyTag=1, algorithm=8, digestType=2, digest="AB")]


def test_dns_ds_removed_by_match():
    dns_sec = DnsSec(ds_data=[DsData(keyTag=1, algorithm=8, digestType=2, digest="AB")])

    result = update(op("remove", "/dns/records", match={"type": "ds"}), dnsSEC=dns_sec)

    assert result.remove.dnsSEC.ds_data == dns_sec.ds_data
    assert result.add is None


def test_changed_addresses_of_a_host_attribute_are_removed_and_added():
    ns = NS(host_objs=None, host_attrs=[HostAttr(id="ns2.foo.example", ipv4=["192.0.2.1", "192.0.2.2"])])

    result = update(op("remove", "/dns/records", match={"rdata": {"address": "192.0.2.2"}}), ns=ns)

    assert [(h.id, h.ipv4) for h in result.add.ns.host_attrs] == [("ns2.foo.example", ["192.0.2.1"])]
    assert [(h.id, h.ipv4) for h in result.remove.ns.host_attrs] == [("ns2.foo.example", ["192.0.2.1", "192.0.2.2"])]


def test_ds_and_dnskey_together_are_unsupported():
    dns = {"@type": "dnsData", "records": [
        {"@type": "dnsRecord", "name": "@", "type": "ds",
         "rdata": {"keyTag": "1", "algorithm": "8", "digestType": "2", "digest": "ab"}},
        {"@type": "dnsRecord", "name": "@", "type": "dnskey",
         "rdata": {"flags": "257", "protocol": "3", "algorithm": "8", "publicKey": "AAAA"}},
    ]}

    with pytest.raises(NotSupportedByProxy):
        update(op("replace", "/dns", value=dns))


def test_nameservers_and_dns_records_cannot_be_mixed():
    dns = {"@type": "dnsData", "records": [
        {"@type": "dnsRecord", "name": "@", "type": "ns", "rdata": {"nsdname": "ns9.foo.example."}},
    ]}

    with pytest.raises(ValueError, match="cannot be used together"):
        update(op("add", "/dns", value=dns))


def test_remove_auth_info_needs_no_current_value():
    result = update(op("remove", "/authInfo"), op("remove", "/nameservers"))

    assert result.change.clear_auth_info is True


def test_other_members_cannot_be_changed():
    with pytest.raises(ValueError, match="expiryDate"):
        update(op("add", "/expiryDate", value="2030-01-01T00:00:00Z"))


def test_result_must_satisfy_the_schema():
    with pytest.raises(Exception):
        update(op("remove", "/name"))


def test_no_matching_element_is_a_422_data_management_policy_violation():
    with pytest.raises(ProblemException) as problem:
        map_request(
            domain_patch.rpp_to_model_with_current, NAME,
            [op("remove", "/contacts", match={"label": "billing"})], current(),
        )

    assert problem.value.status == 422
    assert problem.value.headers["RPP-Code"] == "02308"
    assert "Operation 1" in problem.value.detail


def test_a_status_with_a_due_date_is_unsupported():
    with pytest.raises(NotSupportedByEpp, match="due"):
        update(op("add", "/status", value={**STATUS, "due": "2027-01-01T00:00:00Z"}))


def test_patching_a_status_with_the_reason_it_has_changes_nothing():
    result = update(op("replace", "/status", value=[{**STATUS, "reason": "Same"}]), status=["clientHold"], status_reasons={"clientHold": "Same"})

    assert result.add is None and result.remove is None


def test_replacing_the_reason_of_a_status_is_remove_and_add():
    result = update(op("replace", "/status", value=[{**STATUS, "reason": "New"}]), status=["clientHold"], status_reasons={"clientHold": "Old"})

    assert result.add.status_reasons == {"clientHold": "New"} and result.remove.status == ["clientHold"]


def test_records_of_the_hosts_a_domain_has_as_objects_change_nothing():
    records = [
        {"@type": "dnsRecord", "name": "@", "type": "ns", "rdata": {"nsdname": "NS1.foo.example."}},
        {"@type": "dnsRecord", "name": "@", "type": "ns", "rdata": {"nsdname": "ns2.foo.example."}},
    ]

    result = update(op("remove", "/nameservers"), op("add", "/dns", value={"@type": "dnsData", "records": records}))

    assert result.add is None and result.remove is None


def test_nameservers_with_glue_are_rejected():
    glue = {"@type": "dnsRecord", "name": "ns1.foo.example.", "type": "a", "rdata": {"address": "192.0.2.1"}}

    with pytest.raises(ValueError, match="cannot be used together"):
        update(op("add", "/dns", value={"@type": "dnsData", "records": [glue]}))
