import pytest

from eppclient.eppclient import EPPClient, IDN_EXTENSION, RGP_EXTENSION, SEC_DNS_EXTENSION
from eppclient.tcpclient import ConnectionException

OTHER_EXTENSION = "urn:ietf:params:xml:ns:launch-1.0"
LOGIN_OK = (
    '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response>'
    '<result code="1000"><msg>ok</msg></result></response></epp>'
)


def greeting(*extensions):
    uris = "".join(f"<extURI>{uri}</extURI>" for uri in extensions)
    service_extension = f"<svcExtension>{uris}</svcExtension>" if uris else ""
    return (
        '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><greeting><svID>s</svID><svcMenu><version>1.0</version>'
        f'<lang>en</lang><objURI>urn:ietf:params:xml:ns:domain-1.0</objURI>{service_extension}</svcMenu>'
        '</greeting></epp>'
    )


class ScriptedTransport:
    """Receives the given messages in order, and records what was sent."""

    def __init__(self, *received, fail_connect=False):
        self.received = list(received)
        self.fail_connect = fail_connect
        self.sent = []

    def connect(self):
        if self.fail_connect:
            raise OSError("unreachable")

    def send(self, message):
        self.sent.append(message)

    def receive(self):
        return self.received.pop(0)

    def disconnect(self):
        pass


def connected_client(*extensions):
    transport = ScriptedTransport(greeting(*extensions), LOGIN_OK)
    client = EPPClient(transport, "user", "pw")
    client.connect()
    return client, transport


def test_extensions_come_from_the_greeting():
    client, _ = connected_client(SEC_DNS_EXTENSION, OTHER_EXTENSION)

    assert client.supports_extension(SEC_DNS_EXTENSION)
    assert client.supports_extension(OTHER_EXTENSION)


def test_extension_the_greeting_leaves_out_is_not_supported():
    client, _ = connected_client(OTHER_EXTENSION)

    assert client.connected
    assert not client.supports_extension(SEC_DNS_EXTENSION)


def test_login_takes_only_what_the_proxy_uses_and_the_server_offers():
    _, transport = connected_client(SEC_DNS_EXTENSION, OTHER_EXTENSION)

    assert f"<extURI>{SEC_DNS_EXTENSION}</extURI>" in transport.sent[0]
    assert OTHER_EXTENSION not in transport.sent[0]


def test_login_takes_the_idn_extension_the_server_offers():
    _, transport = connected_client(SEC_DNS_EXTENSION, IDN_EXTENSION)

    assert f"<extURI>{IDN_EXTENSION}</extURI>" in transport.sent[0]


def test_login_takes_the_rgp_extension_the_server_offers():
    """RFC 3915, for the restore process."""
    _, transport = connected_client(SEC_DNS_EXTENSION, RGP_EXTENSION)

    assert f"<extURI>{RGP_EXTENSION}</extURI>" in transport.sent[0]


@pytest.mark.parametrize("extensions", [(), (OTHER_EXTENSION,)])
def test_login_has_no_service_extension_when_the_server_offers_none_the_proxy_uses(extensions):
    _, transport = connected_client(*extensions)

    assert "svcExtension" not in transport.sent[0]


def test_supports_extension_connects_first():
    client = EPPClient(ScriptedTransport(greeting(SEC_DNS_EXTENSION), LOGIN_OK), "user", "pw")

    assert client.supports_extension(SEC_DNS_EXTENSION)
    assert client.connected


def test_unreachable_server_is_no_answer_about_its_extensions():
    client = EPPClient(ScriptedTransport(fail_connect=True), "user", "pw")

    with pytest.raises(ConnectionException):
        client.supports_extension(SEC_DNS_EXTENSION)
