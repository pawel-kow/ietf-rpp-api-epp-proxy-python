import pytest

from core.session.session_pool import SessionPool
from registry_adapter.epp.idn_tables import IdnTables
from registry_adapter.epp.profile import epp_profile
from registry_adapter.epp.session.epp_client import IDN_EXTENSION, SEC_DNS_EXTENSION
from rpp.http.app import create_app
from tests.helper.epp_backends import epp_backends
from tests.helper.fake_epp_client import FakeEppClient
from tests.unit.test_rpp_wire import BODY_HEADERS, check_reply, epp_reply, HEADERS

NAME = "xn--bcher-kva.example"

TABLES = IdnTables({"latn-1.0": "de"})

IDN_SERVER = (SEC_DNS_EXTENSION, IDN_EXTENSION)

IDN_BODY = {"@type": "domainName", "name": NAME, "uName": "bücher.example", "lgr": "latn-1.0"}

CREATE_REPLY = (True, "1000", epp_reply(1000, (
    '<resData><domain:creData xmlns:domain="urn:ietf:params:xml:ns:domain-1.0">'
    f'<domain:name>{NAME.upper()}</domain:name><domain:crDate>2026-11-09T00:00:00.0Z</domain:crDate>'
    '</domain:creData></resData>'
)))

INFO_REPLY = (True, "1000", epp_reply(1000, (
    '<resData><domain:infData xmlns:domain="urn:ietf:params:xml:ns:domain-1.0">'
    f'<domain:name>{NAME.upper()}</domain:name><domain:roid>D1-EX</domain:roid><domain:status s="ok"/>'
    '<domain:clID>foo</domain:clID><domain:crID>foo</domain:crID>'
    '<domain:crDate>2026-11-09T00:00:00.0Z</domain:crDate></domain:infData></resData>'
    '<extension><idn:data xmlns:idn="urn:ietf:params:xml:ns:idn-1.0"><idn:table>de</idn:table>'
    '<idn:uname>bücher.example</idn:uname></idn:data></extension>'
)))


def setup(*replies, extensions=IDN_SERVER, idn_tables=TABLES):
    clients = []

    def factory(username, password):
        client = FakeEppClient(username, password, replies=list(replies), extensions=extensions)
        clients.append(client)
        return client

    idn_tables = idn_tables or IdnTables()
    return create_app(
        SessionPool(epp_backends(factory, idn_tables)), epp_profile(idn_tables),
    ).test_client(), clients


def sent(clients):
    return [message for client in clients for message in client.sent]


def test_create_sends_the_idn_and_reads_it_back():
    http, clients = setup(CREATE_REPLY, INFO_REPLY)

    response = http.post("/domainNames", json=IDN_BODY, headers=BODY_HEADERS)

    assert response.status_code == 201
    assert response.json()["uName"] == "bücher.example"
    assert response.json()["lgr"] == "latn-1.0"
    create = sent(clients)[0]
    assert "<idn:table>de</idn:table>" in create
    assert "<idn:uname>bücher.example</idn:uname>" in create


def test_create_with_an_idn_on_a_server_without_the_extension_is_a_501_unimplemented_extension():
    http, clients = setup(extensions=(SEC_DNS_EXTENSION,))

    response = http.post("/domainNames", json=IDN_BODY, headers=BODY_HEADERS)

    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02103"
    assert sent(clients) == []


@pytest.mark.parametrize("body", [
    {**IDN_BODY, "lgr": "cyrl-1.0"},
    {key: value for key, value in IDN_BODY.items() if key != "lgr"},
])
def test_create_with_an_lgr_without_a_table_or_a_uname_without_an_lgr_is_a_400(body):
    http, clients = setup()

    response = http.post("/domainNames", json=body, headers=BODY_HEADERS)

    assert response.status_code == 400
    assert response.headers["RPP-Code"] == "02001"
    assert sent(clients) == []


def test_create_without_configured_tables_refuses_an_lgr():
    http, _ = setup(idn_tables=None)

    response = http.post("/domainNames", json=IDN_BODY, headers=BODY_HEADERS)

    assert response.status_code == 400


def test_read_has_uname_and_lgr():
    http, _ = setup(INFO_REPLY)

    response = http.get(f"/domainNames/{NAME}", headers=HEADERS)

    assert response.status_code == 200
    assert response.json()["uName"] == "bücher.example"
    assert response.json()["lgr"] == "latn-1.0"


@pytest.mark.parametrize("method", ["get", "head"])
@pytest.mark.parametrize("query", ["uName=b%C3%BCcher.example", "lgr=latn-1.0", "uName=b%C3%BCcher.example&lgr=latn-1.0"])
def test_availability_with_uname_or_lgr_is_a_501(method, query):
    """EPP check has no place for them (draft-obispo-epp-idn-04 adds nothing to check)."""
    http, clients = setup(check_reply(True))

    response = getattr(http, method)(f"/domainNames/{NAME}/availability?{query}", headers=HEADERS)

    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02102"
    assert sent(clients) == []


def test_availability_of_an_a_label_without_parameters_is_checked():
    reply = (True, "1000", epp_reply(1000, (
        '<resData><domain:chkData xmlns:domain="urn:ietf:params:xml:ns:domain-1.0">'
        f'<domain:cd><domain:name avail="1">{NAME}</domain:name></domain:cd></domain:chkData></resData>'
    )))
    http, clients = setup(reply)

    response = http.get(f"/domainNames/{NAME}/availability", headers=HEADERS)

    assert response.status_code == 200
    assert f"{NAME}</domain:name>" in sent(clients)[0].lower()
