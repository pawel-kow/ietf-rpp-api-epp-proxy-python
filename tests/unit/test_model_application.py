"""`apply` turns a partial update into the full one it amounts to, `difference` the other way round. For every update
the direct mappers produce, the round trip gives the update back, up to order (#108)."""
import pytest

from models import (
    Address, AuthInfo, AuthInfoAction, Contact, ContactReference, ContactType, Domain, DsData, DnsSec, Host, HostObj, NS,
    contact_application, contact_difference, domain_application, domain_difference, host_application, host_difference,
)
from rpp_to_model_mapper import contact_patch, domain_patch, host_patch

DOMAIN = "foo.example"
HOST = "ns1.foo.example"
CONTACT = "JD-1"
PASSWORD = {"@type": "authInfo", "method": "authinfo", "authdata": "NewSecret1!x"}


def op(name, path, **members):
    return {"op": name, "path": path, **members}


def canonical(value):
    """The value with every list in a fixed order, so that two updates compare up to order."""
    if isinstance(value, list):
        return sorted((canonical(item) for item in value), key=repr)
    if isinstance(value, dict):
        return {key: canonical(item) for key, item in value.items()}
    if hasattr(value, "__dataclass_fields__"):
        return (type(value).__name__, canonical(vars(value)))
    return value


def current_domain() -> Domain:
    return Domain(
        name=DOMAIN, roid="D1", status=["ok", "clientHold"], status_reasons={"clientHold": "Unpaid"}, clID="foo",
        ns=NS(host_objs=[HostObj(id="ns1.foo.example"), HostObj(id="ns2.foo.example")], host_attrs=None),
        contacts=[ContactReference(id="REG-1", types=["registrant"]), ContactReference(id="REG-2", types=["tech"])],
        dnsSEC=DnsSec(ds_data=[DsData(keyTag=1, algorithm=8, digestType=2, digest="AB")]),
    )


@pytest.mark.parametrize("operations", [
    [op("add", "/nameservers", value={"@type": "host", "hostName": "ns3.foo.example"})],
    [op("remove", "/nameservers", match={"hostName": "ns1.foo.example"})],
    [op("add", "/contacts", value={"label": "admin", "object": {"@type": "contact", "id": "REG-3"}})],
    [op("remove", "/contacts", match={"label": "tech", "object": {"id": "REG-2"}})],
    [op("replace", "/registrant", value={"@type": "contact", "id": "REG-9"})],
    [op("remove", "/registrant")],
    [op("replace", "/authInfo", value=PASSWORD)],
    [op("remove", "/authInfo")],
    [
        op("add", "/nameservers", value={"@type": "host", "hostName": "ns3.foo.example"}),
        op("remove", "/nameservers", match={"hostName": "ns2.foo.example"}),
        op("add", "/contacts", value={"label": "billing", "object": {"@type": "contact", "id": "REG-4"}}),
    ],
])
def test_a_domain_update_survives_the_round_trip(operations):
    delta = domain_patch.rpp_to_model(DOMAIN, operations)
    current = current_domain()

    assert canonical(domain_difference.difference(current, domain_application.apply(current, delta))) == canonical(delta)


def test_applying_a_domain_update_keeps_what_it_does_not_name():
    delta = domain_patch.rpp_to_model(DOMAIN, [op("remove", "/nameservers", match={"hostName": "ns1.foo.example"})])

    wanted = domain_application.apply(current_domain(), delta)

    assert [host.id for host in wanted.ns.host_objs] == ["ns2.foo.example"]
    assert wanted.registrant == "REG-1" and [(c.type, c.contact.id) for c in wanted.contacts] == [("tech", "REG-2")]
    assert wanted.status == ["clientHold"] and wanted.status_reasons == {"clientHold": "Unpaid"}
    assert wanted.dnsSEC.ds_data == [DsData(keyTag=1, algorithm=8, digestType=2, digest="AB")]
    assert wanted.auth_info.action == AuthInfoAction.KEEP


def current_contact() -> Contact:
    return Contact(
        id=CONTACT, type=ContactType.PERSON, name="John Doe", email=["a@example.example"], phone=["+49.123"],
        address=Address(street=["1 Main"], city="Berlin", country="DE"), status=["ok", "clientDeleteProhibited"],
        clID="foo", authInfo=AuthInfo(pw="Secret1!x"),
    )


@pytest.mark.parametrize("operations", [
    [op("add", "/status", value={"@type": "contactStatus", "label": "clientUpdateProhibited", "reason": "why"})],
    [op("remove", "/status", match={"label": "clientDeleteProhibited"})],
    [op("replace", "/authInfo", value=PASSWORD)],
    [op("replace", "/contactInfo/emails/email/address", value="b@example.example")],
    [op("replace", "/contactInfo/phones/voice/number", value="tel:+49.999")],
    [op("add", "/contactInfo/phones/fax", value={"number": "tel:+49.888", "features": {"fax": True}})],
])
def test_a_contact_update_survives_the_round_trip(operations):
    delta = contact_patch.rpp_to_model(CONTACT, operations)
    current = current_contact()

    assert canonical(contact_difference.difference(current, contact_application.apply(current, delta))) == canonical(delta)


def current_host() -> Host:
    return Host(name=HOST, ipv4=["192.0.2.1"], ipv6=["2001:db8::1"], status=["ok", "clientDeleteProhibited"], clID="foo")


def address(record_type, value):
    return {"@type": "dnsRecord", "name": "@", "type": record_type, "rdata": {"address": value}}


@pytest.mark.parametrize("operations", [
    [op("add", "/dns/records", value=address("a", "192.0.2.2"))],
    [op("remove", "/dns/records", match={"type": "aaaa", "rdata": {"address": "2001:db8::1"}})],
    [op("add", "/status", value={"@type": "hostStatus", "label": "clientUpdateProhibited"})],
    [op("remove", "/status", match={"label": "clientDeleteProhibited"})],
    [op("replace", "/hostName", value="ns2.foo.example")],
])
def test_a_host_update_survives_the_round_trip(operations):
    delta = host_patch.rpp_to_model(HOST, operations)
    current = current_host()

    assert canonical(host_difference.difference(current, host_application.apply(current, delta))) == canonical(delta)
