from registry_adapter.epp.gateways.epp_backend import EppBackend
from core.result.error_response import ErrorResponse
from core.result.result_code import ResultCode
from tests.helper.fake_epp_client import FakeEppClient
from tests.helper.epp_ns_map import EPP_NS_MAP

MISSING = (False, "2303", (
    '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response><result code="2303"><msg>Missing</msg></result>'
    '<trID><svTRID>sv-1</svTRID></trID></response></epp>'
))


def backend(**options):
    return EppBackend(FakeEppClient("Foo", "pw", **options), EPP_NS_MAP)


def test_the_sponsor_id_is_the_login():
    assert backend().sponsor_id == "Foo"


def test_the_session_is_the_epp_clients():
    epp = backend()

    epp.connect()

    assert epp.connected and epp.epp_client.connected


def test_an_unreachable_registry_leaves_the_session_closed():
    epp = backend(reachable=False)

    epp.connect()

    assert not epp.connected


def test_disconnect_closes_the_epp_session():
    epp = backend()
    epp.connect()

    epp.disconnect()

    assert not epp.connected and epp.epp_client.disconnect_calls == 1


def test_the_credentials_are_those_of_the_epp_login():
    epp = backend()

    assert epp.verify_credentials("Foo", "pw")
    assert not epp.verify_credentials("Foo", "other")


def test_every_gateway_sends_over_the_same_epp_session():
    epp = backend(reply=MISSING)

    epp.domains.info("a.example")
    epp.contacts.info("C1")
    epp.hosts.info("ns1.a.example")
    epp.messages.ack("12")

    sent = epp.epp_client.sent
    assert ["domain:info" in sent[0], "contact:info" in sent[1], "host:info" in sent[2], 'op="ack"' in sent[3]] == [True] * 4


def test_a_registry_error_is_an_error_response_not_an_exception():
    result = backend(reply=MISSING).domains.info("a.example", client_transaction_id="cl-1")

    assert isinstance(result, ErrorResponse) and result.code == ResultCode.OBJECT_DOES_NOT_EXIST
