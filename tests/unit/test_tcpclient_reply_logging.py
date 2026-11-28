"""The reply to a command that was not loggable is not printed: it can hold what the command asked for."""
from registry_adapter.common.transport.tcp_client import TCPClient
from tests.helper.loopback_epp_server import LoopbackEppServer

SECRET = "<contact:verificationReference>ABC123/45GHT</contact:verificationReference>"


def received(capsys, loggable):
    with LoopbackEppServer(SECRET.encode()) as server:
        client = TCPClient("127.0.0.1", server.port)
        client.connect()
        reply = client.receive() if loggable else client.receive(loggable=False)
        client.disconnect()
    return reply, capsys.readouterr().out


def test_a_loggable_reply_is_printed(capsys):
    reply, out = received(capsys, True)

    assert reply == SECRET and "ABC123/45GHT" in out


def test_the_reply_to_a_command_that_was_not_loggable_is_returned_and_not_printed(capsys):
    reply, out = received(capsys, False)

    assert reply == SECRET
    assert "ABC123" not in out
