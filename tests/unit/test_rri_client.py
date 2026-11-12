"""The RRI session: LOGIN without a greeting, LOGOUT, re-login on a closed session, no retry of a written command."""
import pytest

from registry_adapter.common.transport.tcp_client import ConnectionException
from registry_adapter.rri.session.rri_client import RriClient
from registry_adapter.rri.xml.generated.domain_5_0 import Check
from registry_adapter.rri.xml.generated.global_5_0 import RegistryRequest
from tests.helper.fake_rri_client import error, reply


class FakeTransport:
    def __init__(self, replies, closed=False, fail_send=0):
        self.replies = list(replies)
        self.sent = []
        self.logged = []
        self.closed = closed
        self.fail_send = fail_send
        self.connects = 0

    def connect(self):
        self.connects += 1

    def disconnect(self):
        pass

    def closed_by_peer(self):
        closed, self.closed = self.closed, False
        return closed

    def send(self, message, loggable=True):
        if self.fail_send:
            self.fail_send -= 1
            raise OSError("broken pipe")
        self.sent.append(message)
        self.logged.append(loggable)

    def receive(self):
        return self.replies.pop(0)


CHECK = RegistryRequest(registry_denic_de_domain_5_0_check=Check(handle="x.de"))


def test_login_is_the_first_request_and_holds_the_credentials_unlogged():
    transport = FakeTransport([reply(), reply()])
    client = RriClient(transport, "DENIC-1000022-RRI", "s3cret")

    client.send(CHECK)

    assert "<login><user>DENIC-1000022-RRI</user><password>s3cret</password></login>" in transport.sent[0]
    assert transport.logged == [False, True]
    assert client.connected and client.regacc_id == "DENIC-1000022"


def test_a_refused_login_leaves_no_session():
    transport = FakeTransport([error("83000000010", "Login failed")])
    client = RriClient(transport, "DENIC-1000022-RRI", "wrong")

    client.connect()

    assert not client.connected


def test_a_session_the_server_closed_is_opened_again():
    transport = FakeTransport([reply(), reply(), reply(), reply()])
    client = RriClient(transport, "DENIC-1000022-RRI", "pw")
    client.send(CHECK)

    transport.closed = True
    client.send(CHECK)

    assert transport.connects == 2
    assert "<login>" in transport.sent[2]


def test_a_command_that_was_never_written_is_sent_on_a_new_session():
    transport = FakeTransport([reply(), reply(), reply()])
    client = RriClient(transport, "DENIC-1000022-RRI", "pw")
    client.connect()
    transport.fail_send = 1

    client.send(CHECK)

    assert sum("<domain:check>" in m for m in transport.sent) == 1


def test_a_lost_reply_is_not_retried():
    transport = FakeTransport([reply()])
    client = RriClient(transport, "DENIC-1000022-RRI", "pw")
    client.connect()

    with pytest.raises(IndexError):
        client.send(CHECK)
    assert sum("<domain:check>" in m for m in transport.sent) == 1


def test_logout_on_disconnect():
    transport = FakeTransport([reply(), reply()])
    client = RriClient(transport, "DENIC-1000022-RRI", "pw")
    client.connect()

    client.disconnect()

    assert "<logout" in transport.sent[1] and not client.connected


def test_an_unreachable_server_is_a_connection_error():
    transport = FakeTransport([error("83000000010", "Login failed")])
    client = RriClient(transport, "DENIC-1000022-RRI", "pw")

    with pytest.raises(ConnectionException):
        client.send(CHECK)
