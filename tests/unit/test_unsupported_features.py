from functools import partial

import pytest
from connexion import ProblemException

from controller.helper.rpp_response import map_request
from eppclient.epp_profile import EPP_PROFILE
from tests.helper.epp_app_context import epp_app_context  # noqa: F401, a fixture
from models import ResultCode
from rpp_to_model_mapper import (
    NotSupportedByBackend, NotSupportedByProxy, contacts, domain_patch, domains, host_patch, host_replacement, hosts,
)

pytestmark = pytest.mark.usefixtures("epp_app_context")

create_domain = partial(domains.rpp_to_model, profile=EPP_PROFILE)

DOMAIN = {"@type": "domainName", "name": "foo.example"}
HOST = {"@type": "host", "hostName": "ns1.foo.example"}
EMAIL = {"address": "a@example.com"}
TTL = {"@type": "dnsControls", "ttl": {"a": 3600}}
SIG_LIFETIME = {"@type": "dnsControls", "maxSigLifetime": {"ds": 3600}}


def replace_host(body):
    """A full update of the host the body names."""
    return host_replacement.rpp_to_model("ns1.foo.example", body)


def card(**members):
    return {"@type": "Card", "version": "2.0", "kind": "individual", "name": {"full": "John Doe"}, **members}


def contact(contact_card=None, **members):
    return {"@type": "contact", "id": "c1", "contactInfo": contact_card or card(), **members}


def record(kind, rdata, name="@", **members):
    return {"@type": "dnsRecord", "name": name, "type": kind, "rdata": rdata, **members}


def dns(*records, **members):
    return {"@type": "dnsData", "records": list(records), **members}


DS = record("ds", {"keyTag": "1", "algorithm": "3", "digestType": "1", "digest": "AB"})
KEY = record("dnskey", {"flags": "257", "protocol": "3", "algorithm": "8", "publicKey": "AQPJ"})
ADDRESS = {"address": "192.0.2.1"}
STATUS = {"@type": "hostStatus", "label": "clientUpdateProhibited"}
DOMAIN_STATUS = [{"@type": "domainStatus", "label": "clientHold"}]


def op(operation, path, **members):
    return [{"op": operation, "path": path, **members}]


NOT_IN_EPP = [
    (create_domain, {**DOMAIN, "status": DOMAIN_STATUS}),
    (create_domain, {**DOMAIN, "contacts": [{"label": "reseller", "object": {"@type": "contact", "id": "c1"}}]}),
    (create_domain, {**DOMAIN, "authInfo": {"@type": "authInfo", "method": "other", "authdata": "x"}}),
    (create_domain, {**DOMAIN, "dns": dns(record("mx", {"exchange": "a.", "preference": "1"}))}),
    (create_domain, {**DOMAIN, "dns": dns(record("ns", {"nsdname": "a."}, **{"class": "CH"}))}),
    (create_domain, {**DOMAIN, "dns": dns(record("a", ADDRESS, name="www"))}),
    (create_domain, {**DOMAIN, "dns": dns(record("ns", {"nsdname": "a."}, name="sub"))}),
    (hosts.rpp_to_model, {**HOST, "status": [STATUS]}),
    (hosts.rpp_to_model, {**HOST, "dns": dns(record("a", ADDRESS, name="other.example."))}),
    (hosts.rpp_to_model, {**HOST, "dns": dns(record("ns", {"nsdname": "other.example."}))}),
    (hosts.rpp_to_model, {**HOST, "dns": dns(record("mx", {"exchange": "a.", "preference": "1"}))}),
    (hosts.rpp_to_model, {**HOST, "dns": dns(controls=SIG_LIFETIME)}),
    (replace_host, {**HOST, "status": [{**STATUS, "due": "2030-01-01T00:00:00Z"}]}),
    (contacts.rpp_to_model, contact(status=[{"@type": "contactStatus", "label": "clientUpdateProhibited"}])),
    (contacts.rpp_to_model, contact(card(links={"url": {"uri": "https://example.example"}}))),
    (contacts.rpp_to_model, contact(card(emails={"email": EMAIL, "email-1": EMAIL}))),
    (contacts.rpp_to_model, contact(card(organizations={"org": {"name": "Org"}}))),
]

NOT_IN_PROXY = [
    (create_domain, {**DOMAIN, "dns": dns(controls=SIG_LIFETIME)}),
    (create_domain, {**DOMAIN, "dns": dns(DS, KEY)}),
    (contacts.rpp_to_model, contact(disclose={"@type": "disclose"})),
]

NOT_IN_EPP_PATCH = [
    (host_patch.rpp_to_model, "ns1.foo.example", op("remove", "/hostName")),
    (host_patch.rpp_to_model, "ns1.foo.example", op(
        "add", "/dns/records", value=record("ns", {"nsdname": "other.example."}),
    )),
]


def rejection(mapper, *args):
    with pytest.raises(ProblemException) as rejected:
        map_request(mapper, *args)
    return rejected.value


def raised_by(mapper, *args):
    with pytest.raises((NotSupportedByBackend, NotSupportedByProxy)) as raised:
        mapper(*args)
    return raised.value


@pytest.mark.parametrize("case", NOT_IN_EPP + NOT_IN_EPP_PATCH)
def test_what_epp_cannot_hold_is_unimplemented_option(case):
    assert isinstance(raised_by(*case), NotSupportedByBackend)
    problem = rejection(*case)
    assert problem.status == 501
    assert problem.headers["RPP-Code"] == "02102"
    assert "cannot be expressed in EPP" in problem.detail


@pytest.mark.parametrize("case", NOT_IN_PROXY)
def test_what_only_the_proxy_lacks_is_unimplemented_option(case):
    assert isinstance(raised_by(*case), NotSupportedByProxy)
    problem = rejection(*case)
    assert problem.status == 501
    assert problem.headers["RPP-Code"] == "02102"
    assert "not by this proxy" in problem.detail


@pytest.mark.parametrize("case", [
    (create_domain, {**DOMAIN, "dns": dns(controls=TTL)}),
    (create_domain, {**DOMAIN, "dns": dns(controls={**TTL, **SIG_LIFETIME})}),
    (hosts.rpp_to_model, {**HOST, "dns": dns(controls=TTL)}),
    (replace_host, {**HOST, "dns": dns(controls=TTL)}),
])
def test_ttl_needs_an_extension_the_proxy_lacks(case):
    assert isinstance(raised_by(*case), NotSupportedByProxy)
    problem = rejection(*case)
    assert problem.status == 501
    assert problem.headers["RPP-Code"] == "02103"
    assert problem.title == ResultCode.UNIMPLEMENTED_EXTENSION.value[1]
    assert problem.detail == "'dns.controls.ttl' needs RFC 9803, which this proxy does not implement"
