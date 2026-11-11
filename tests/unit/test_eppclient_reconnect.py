import select
import socket
import struct
import threading

import pytest

from registry_adapter.common.transport.tcp_client import ConnectionException, TCPClient
from registry_adapter.epp.session.epp_client import EPPClient

GREETING = (
    '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><greeting><svID>s</svID><svcMenu><version>1.0</version>'
    '<lang>en</lang><objURI>urn:ietf:params:xml:ns:domain-1.0</objURI></svcMenu></greeting></epp>'
)

OK = (
    '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response>'
    '<result code="1000"><msg>ok</msg></result></response></epp>'
)

COMMAND = "<check/>"


class SessionTransport:
    """
    A transport that greets on every connect and answers every message with OK.
    Its failures are set per test.
    """

    def __init__(self):
        self.sessions = 0
        self.sent = []
        self.received = []
        self.closed = False
        self.send_failures = 0
        self.receive_failure = False
        self.connect_failure = False

    def connect(self):
        if self.connect_failure:
            raise OSError("unreachable")
        self.sessions += 1
        self.closed = False
        self.received = [GREETING]

    def closed_by_peer(self):
        return self.closed

    def send(self, message):
        if self.send_failures and "<login>" not in message:
            self.send_failures -= 1
            raise OSError("EOF occurred in violation of protocol")
        self.sent.append(message)
        self.received.append(OK)

    def receive(self):
        if self.receive_failure and self.sent[-1] == COMMAND:
            raise ConnectionException("Connection closed by server")
        return self.received.pop(0)

    def disconnect(self):
        pass


def logged_in():
    transport = SessionTransport()
    client = EPPClient(transport, "user", "pw")
    client.connect()
    return client, transport


def commands(transport):
    return [message for message in transport.sent if message == COMMAND]


def test_a_session_the_server_closed_is_logged_in_again_before_the_command():
    client, transport = logged_in()
    transport.closed = True

    success, code, _ = client.send_and_get_response(COMMAND)

    assert (success, code) == (True, "1000")
    assert transport.sessions == 2
    assert commands(transport) == [COMMAND]


def test_an_open_session_is_kept():
    client, transport = logged_in()

    client.send_and_get_response(COMMAND)

    assert transport.sessions == 1


def test_a_failed_send_is_sent_again_on_a_new_session():
    client, transport = logged_in()
    transport.send_failures = 1

    success, code, _ = client.send_and_get_response(COMMAND)

    assert (success, code) == (True, "1000")
    assert transport.sessions == 2
    assert commands(transport) == [COMMAND]


def test_a_send_is_retried_only_once():
    client, transport = logged_in()
    transport.send_failures = 2

    with pytest.raises(OSError):
        client.send_and_get_response(COMMAND)

    assert transport.sessions == 2
    assert not client.connected


def test_a_failed_receive_is_not_retried():
    client, transport = logged_in()
    transport.receive_failure = True

    with pytest.raises(ConnectionException):
        client.send_and_get_response(COMMAND)

    # The server may have run the command, so it is sent once.
    assert commands(transport) == [COMMAND]
    assert transport.sessions == 1
    assert not client.connected


def test_without_a_session_no_command_is_sent():
    client, transport = logged_in()
    transport.closed = True
    transport.connect_failure = True

    with pytest.raises(ConnectionException):
        client.send_and_get_response(COMMAND)

    assert commands(transport) == []


def frame(text):
    payload = text.encode()
    return struct.pack('>L', len(payload) + 4) + payload


def read_frame(connection):
    length = struct.unpack('>L', connection.recv(4, socket.MSG_WAITALL))[0]
    return connection.recv(length - 4, socket.MSG_WAITALL).decode()


def test_over_tcp_a_session_closed_while_idle_is_logged_in_again():
    listener = socket.create_server(("127.0.0.1", 0))
    listener.settimeout(5)
    first_closed = threading.Event()
    received = []

    def serve():
        with listener:
            # The first session idles out after the login.
            with listener.accept()[0] as connection:
                connection.sendall(frame(GREETING))
                received.append(read_frame(connection))
                connection.sendall(frame(OK))
            first_closed.set()
            with listener.accept()[0] as connection:
                connection.sendall(frame(GREETING))
                for _ in range(2):
                    received.append(read_frame(connection))
                    connection.sendall(frame(OK))
                connection.recv(1)

    server = threading.Thread(target=serve, daemon=True)
    server.start()
    client = EPPClient(TCPClient("127.0.0.1", listener.getsockname()[1]), "user", "pw")
    client.connect()
    assert first_closed.wait(5)
    # Let the close reach the client.
    select.select([client.client.socket], [], [], 5)

    success, code, _ = client.send_and_get_response(COMMAND)

    client.disconnect(send_logout=False)
    server.join(5)
    assert (success, code) == (True, "1000")
    assert ["<login>" in message for message in received] == [True, True, False]
    assert received[-1] == COMMAND
