import pytest
from jsonschema import ValidationError

from models import ContactReference, Domain, DsData, DnsSec, HostAttr, HostObj, NS
from rpp_to_model_mapper import NotSupportedByEpp, NotSupportedByProxy, domain_replacement, domains

NAME = "foo.example"
DS = {"@type": "dnsRecord", "name": "@", "type": "ds", "rdata": {
    "keyTag": "1", "algorithm": "8", "digestType": "2", "digest": "AB"}}
NS_RECORD = {"@type": "dnsRecord", "name": "@", "type": "ns", "rdata": {"nsdname": "ns9.foo.example."}}


def host(name):
    return {"@type": "host", "hostName": name}


def contact(label, contact_id):
    return {"label": label, "object": {"@type": "contact", "id": contact_id}}


def status(label, **members):
    return {"@type": "domainStatus", "label": label, **members}


def current(**members):
    domain = Domain(
        name=NAME, roid="D1", status=["ok"], crDate="2026-11-04T10:00:00Z", clID="foo", crID="foo",
        ns=NS(host_objs=[HostObj(id="ns1.foo.example"), HostObj(id="ns2.foo.example")], host_attrs=None),
        contacts=[ContactReference(id="REG-1", types=["registrant"]), ContactReference(id="REG-2", types=["tech"])],
    )
    for member, value in members.items():
        setattr(domain, member, value)
    return domains.model_to_rpp(domain)


def replace(body_members, **domain_members):
    body = {"@type": "domainName", **body_members}
    return domain_replacement.rpp_to_model_with_current(NAME, domain_replacement.rpp_to_model(NAME, body), current(**domain_members))


STAYS = {
    "nameservers": [host("ns1.foo.example"), host("ns2.foo.example")],
    "registrant": {"@type": "contact", "id": "REG-1"},
    "contacts": [contact("tech", "REG-2")],
}


def ids(ns):
    return [host.id for host in ns.host_objs]


def test_the_same_state_changes_nothing():
    result = replace(STAYS)

    assert result.add is None and result.remove is None and result.change is None


def test_omitted_members_are_cleared():
    result = replace({})

    assert ids(result.remove.ns) == ["ns1.foo.example", "ns2.foo.example"]
    assert sorted((c.type, c.contact.id) for c in result.remove.contacts) == [("registrant", ""), ("tech", "REG-2")]
    assert result.add is None


def test_nameservers_are_replaced():
    result = replace({**STAYS, "nameservers": [host("ns2.foo.example"), host("ns3.foo.example")]})

    assert ids(result.add.ns) == ["ns3.foo.example"]
    assert ids(result.remove.ns) == ["ns1.foo.example"]


def test_registrant_and_contacts_are_replaced():
    result = replace({**STAYS, "registrant": {"@type": "contact", "id": "REG-9"}, "contacts": [contact("admin", "REG-3")]})

    assert sorted((c.type, c.contact.id) for c in result.add.contacts) == [("admin", "REG-3"), ("registrant", "REG-9")]
    assert [(c.type, c.contact.id) for c in result.remove.contacts] == [("tech", "REG-2")]


def test_client_status_is_a_set_replace_and_server_status_stays():
    result = replace(
        {**STAYS, "status": [status("clientHold", reason="Late")]},
        status=["clientUpdateProhibited", "serverHold"],
    )

    assert result.add.status == ["clientHold"]
    assert result.add.status_reasons == {"clientHold": "Late"}
    assert result.remove.status == ["clientUpdateProhibited"]


def test_omitted_status_clears_the_client_statuses_and_validates_with_none_left():
    result = replace(STAYS, status=["clientHold", "clientUpdateProhibited"])

    assert result.remove.status == ["clientHold", "clientUpdateProhibited"]
    assert result.add is None


def test_a_new_reason_is_remove_and_add():
    result = replace(
        {**STAYS, "status": [status("clientHold", reason="New")]},
        status=["clientHold"], status_reasons={"clientHold": "Old"},
    )

    assert result.add.status == ["clientHold"] and result.remove.status == ["clientHold"]
    assert result.add.status_reasons == {"clientHold": "New"}


def test_the_same_reason_changes_nothing():
    result = replace(
        {**STAYS, "status": [status("clientHold", reason="Same")]},
        status=["clientHold"], status_reasons={"clientHold": "Same"},
    )

    assert result.add is None and result.remove is None


def test_dropping_a_reason_is_a_change():
    result = replace({**STAYS, "status": [status("clientHold")]}, status=["clientHold"], status_reasons={"clientHold": "Old"})

    assert result.add.status == ["clientHold"] and result.remove.status == ["clientHold"]
    assert result.add.status_reasons is None


def test_a_status_with_a_due_date_is_unsupported():
    with pytest.raises(NotSupportedByEpp, match="due"):
        replace({**STAYS, "status": [status("clientHold", due="2027-01-01T00:00:00Z")]})


@pytest.mark.parametrize("members", [
    {"registrant": {"@type": "contact", "id": "R1", "foo": "bar"}},
    {"contacts": [{"label": "tech", "object": {"@type": "contact", "id": "R1", "foo": "bar"}}]},
    {"contacts": [{"label": "tech", "foo": "bar", "object": {"@type": "contact", "id": "R1"}}]},
    {"nameservers": [{"@type": "host", "hostName": "ns1.foo.example", "foo": "bar"}]},
    {"status": [{"@type": "domainStatus", "label": "clientHold", "foo": "bar"}]},
    {"authInfo": {"@type": "authInfo", "method": "authinfo", "authdata": "x", "foo": "bar"}},
])
def test_an_undeclared_nested_member_is_rejected(members):
    with pytest.raises(ValueError, match="Undeclared"):
        domain_replacement.rpp_to_model(NAME, {"@type": "domainName", **members})


def test_an_auth_info_method_other_than_authinfo_is_unsupported():
    with pytest.raises(NotSupportedByEpp):
        replace({**STAYS, "authInfo": {"@type": "authInfo", "method": "other", "authdata": "x"}})


def test_contacts_with_several_roles_are_compared_by_role_and_id():
    result = replace({**STAYS, "contacts": [contact("tech", "REG-2"), contact("admin", "REG-2"), contact("billing", "REG-2")]})

    assert sorted((c.type, c.contact.id) for c in result.add.contacts) == [("admin", "REG-2"), ("billing", "REG-2")]
    assert result.remove is None


def owns(name, *addresses):
    return [
        {"@type": "dnsRecord", "name": "@", "type": "ns", "rdata": {"nsdname": f"{name}."}},
        *({"@type": "dnsRecord", "name": f"{name}.", "type": "a", "rdata": {"address": address}} for address in addresses),
    ]


WITHOUT_NAMESERVERS = {k: v for k, v in STAYS.items() if k != "nameservers"}


def with_records(*records):
    return {**WITHOUT_NAMESERVERS, "dns": {"@type": "dnsData", "records": list(records)}}


def test_host_objects_to_records_of_the_same_hosts_change_nothing():
    result = replace(with_records(*owns("NS1.foo.example"), *owns("ns2.foo.example")))

    assert result.add is None and result.remove is None


def test_records_to_host_objects_of_the_same_hosts_change_nothing():
    current_ns = NS(host_objs=None, host_attrs=[HostAttr(id="ns1.foo.example"), HostAttr(id="NS2.foo.example")])

    result = replace(STAYS, ns=current_ns)

    assert result.add is None and result.remove is None


def test_host_objects_to_records_of_other_hosts_are_replaced():
    result = replace(with_records(*owns("ns1.foo.example"), *owns("ns9.foo.example")))

    assert [h.id for h in result.add.ns.host_attrs] == ["ns9.foo.example"]
    assert ids(result.remove.ns) == ["ns2.foo.example"]


def test_records_to_other_host_objects_swap_the_whole_delegation():
    """EPP takes one form or the other, and a registry that shows host attributes stores them."""
    current_ns = NS(host_objs=None, host_attrs=[HostAttr(id="ns1.foo.example"), HostAttr(id="ns2.foo.example")])

    result = replace({**STAYS, "nameservers": [host("ns1.foo.example"), host("ns9.foo.example")]}, ns=current_ns)

    assert ids(result.add.ns) == ["ns1.foo.example", "ns9.foo.example"]
    assert [h.id for h in result.remove.ns.host_attrs] == ["ns1.foo.example", "ns2.foo.example"]


def test_records_with_addresses_over_host_objects_are_removed_and_added():
    result = replace(with_records(*owns("ns1.foo.example", "192.0.2.1"), *owns("ns2.foo.example")))

    assert [(h.id, h.ipv4) for h in result.add.ns.host_attrs] == [("ns1.foo.example", ["192.0.2.1"])]
    assert ids(result.remove.ns) == ["ns1.foo.example"]


def test_host_objects_over_records_with_addresses_are_removed_and_added():
    current_ns = NS(host_objs=None, host_attrs=[HostAttr(id="ns1.foo.example", ipv4=["192.0.2.1"]), HostAttr(id="ns2.foo.example")])

    result = replace(STAYS, ns=current_ns)

    assert ids(result.add.ns) == ["ns1.foo.example", "ns2.foo.example"]
    assert [h.id for h in result.remove.ns.host_attrs] == ["ns1.foo.example", "ns2.foo.example"]


def test_a_change_of_glue_is_remove_and_add():
    current_ns = NS(host_objs=None, host_attrs=[HostAttr(id="ns1.foo.example", ipv4=["192.0.2.1"])])

    result = replace(with_records(*owns("ns1.foo.example", "192.0.2.2")), ns=current_ns)

    assert result.add.ns.host_attrs[0].ipv4 == ["192.0.2.2"]
    assert result.remove.ns.host_attrs[0].ipv4 == ["192.0.2.1"]


def test_glue_out_of_the_zone_in_the_stored_domain_does_not_block_a_change():
    current_ns = NS(host_objs=None, host_attrs=[HostAttr(id="ns1.bar.example", ipv4=["192.0.2.1"])])

    result = replace(WITHOUT_NAMESERVERS, ns=current_ns)

    assert [h.id for h in result.remove.ns.host_attrs] == ["ns1.bar.example"]


def test_nameservers_with_glue_are_rejected_like_ns_records():
    glue = {"@type": "dnsRecord", "name": "ns1.foo.example.", "type": "a", "rdata": {"address": "192.0.2.1"}}

    with pytest.raises(ValueError, match="cannot be used together"):
        replace({**STAYS, "dns": {"@type": "dnsData", "records": [glue]}})


def test_ds_to_dnskey_removes_the_ds_and_adds_the_key():
    dns_sec = DnsSec(ds_data=[DsData(keyTag=1, algorithm=8, digestType=2, digest="AB")])
    key = {"@type": "dnsRecord", "name": "@", "type": "dnskey", "rdata": {
        "flags": "257", "protocol": "3", "algorithm": "8", "publicKey": "AQID"}}

    result = replace({**STAYS, "dns": {"@type": "dnsData", "records": [key]}}, dnsSEC=dns_sec)

    assert result.add.dnsSEC.key_data[0].flags == 257 and result.add.dnsSEC.ds_data is None
    assert result.remove.dnsSEC.ds_data == dns_sec.ds_data


@pytest.mark.parametrize("label", ["ok", "serverHold"])
def test_a_status_of_the_server_is_rejected(label):
    with pytest.raises(ValidationError):
        domain_replacement.rpp_to_model(NAME, {"@type": "domainName", "status": [status(label)]})


@pytest.mark.parametrize("member", ["name", "provMetadata", "expiryDate", "subordinateHosts", "uName", "lgr", "processes"])
def test_a_member_outside_the_update_is_rejected(member):
    with pytest.raises(ValueError, match=member):
        domain_replacement.rpp_to_model(NAME, {"@type": "domainName", member: "x"})


def test_auth_info_present_is_always_sent():
    auth = {"@type": "authInfo", "method": "authinfo", "authdata": "Pw1"}

    result = replace({**STAYS, "authInfo": auth})

    assert result.change.authInfo.pw == "Pw1"


def test_auth_info_omitted_is_left_alone():
    assert replace(STAYS).change is None


def test_nameservers_with_ns_records_are_rejected():
    with pytest.raises(ValueError, match="cannot be used together"):
        replace({**STAYS, "dns": {"@type": "dnsData", "records": [NS_RECORD]}})


def test_nameservers_with_a_ds_record_are_allowed():
    result = replace({**STAYS, "dns": {"@type": "dnsData", "records": [DS]}})

    assert result.add.dnsSEC.ds_data == [DsData(keyTag=1, algorithm=8, digestType=2, digest="AB")]
    assert result.remove is None


def test_omitted_dns_removes_the_ds_record():
    dns_sec = DnsSec(ds_data=[DsData(keyTag=1, algorithm=8, digestType=2, digest="AB")])

    result = replace(STAYS, dnsSEC=dns_sec)

    assert result.remove.dnsSEC.ds_data == dns_sec.ds_data


def test_delegation_by_records_replaces_host_attributes():
    ns = NS(host_objs=None, host_attrs=[HostAttr(id="ns1.foo.example")])
    wanted = {**{k: v for k, v in STAYS.items() if k != "nameservers"}, "dns": {"@type": "dnsData", "records": [NS_RECORD]}}

    result = replace(wanted, ns=ns)

    assert [h.id for h in result.add.ns.host_attrs] == ["ns9.foo.example"]
    assert [h.id for h in result.remove.ns.host_attrs] == ["ns1.foo.example"]


def test_ds_and_dnskey_together_are_unsupported():
    key = {"@type": "dnsRecord", "name": "@", "type": "dnskey", "rdata": {
        "flags": "257", "protocol": "3", "algorithm": "8", "publicKey": "AQID"}}

    with pytest.raises(NotSupportedByProxy):
        replace({"dns": {"@type": "dnsData", "records": [DS, key]}})


def test_ttl_is_unsupported():
    with pytest.raises(NotSupportedByProxy):
        replace({**STAYS, "dns": {"@type": "dnsData", "controls": {"@type": "dnsControls", "ttl": {"a": 3600}}}})


def test_an_unknown_contact_label_is_unsupported():
    with pytest.raises(NotSupportedByEpp):
        replace({**STAYS, "contacts": [contact("other", "REG-2")]})


def test_a_repeated_reason_that_is_empty_changes_nothing():
    result = replace({**STAYS, "status": [status("clientHold", reason="")]}, status=["clientHold"])

    assert result.add is None and result.remove is None


def test_stored_glue_out_of_the_zone_does_not_block_a_put_that_echoes_the_read():
    current_ns = NS(host_objs=None, host_attrs=[HostAttr(id="ns1.bar.example", ipv4=["192.0.2.1"])])
    echo = {**WITHOUT_NAMESERVERS, "dns": current(ns=current_ns)["dns"]}

    result = replace(echo, ns=current_ns)

    assert result.add is None and result.remove is None
