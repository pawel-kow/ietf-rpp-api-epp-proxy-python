import struct

import pytest

from registry_adapter.common.transport.tcp_client import LENGTH_OF_PAYLOAD, ConnectionException, TCPClient


class FakeSocket:
    def __init__(self, payload: bytes):
        self.data = struct.pack('>L', len(payload) + 4) + payload

    def recv(self, size):
        chunk, self.data = self.data[:size], self.data[size:]
        return chunk


def test_receive_decodes_utf8():
    client = TCPClient("host", 700)
    client.socket = FakeSocket("<msg>Jörg</msg>".encode("utf-8"))

    assert client.receive() == "<msg>Jörg</msg>"


def test_receive_rejects_a_message_that_is_not_utf8():
    client = TCPClient("host", 700)
    client.socket = FakeSocket("<msg>Jörg</msg>".encode("latin-1"))

    with pytest.raises(ConnectionException):
        client.receive()


class TricklingSocket(FakeSocket):
    """Returns at most `limit` bytes per recv(), as a socket may."""

    def __init__(self, payload: bytes, limit: int):
        super().__init__(payload)
        self.limit = limit

    def recv(self, size):
        return super().recv(min(size, self.limit))


def test_receive_reassembles_a_payload_split_over_several_reads():
    client = TCPClient("host", 700)
    client.socket = TricklingSocket(b"<msg>split</msg>", 5)

    assert client.receive() == "<msg>split</msg>"


def test_receive_reassembles_a_split_length_header():
    client = TCPClient("host", 700)
    client.socket = TricklingSocket(b"<msg>split</msg>", 1)

    assert client.receive() == "<msg>split</msg>"


def test_receive_leaves_the_next_message_on_the_socket():
    client = TCPClient("host", 700)
    client.socket = FakeSocket(b"<first/>")
    client.socket.data += FakeSocket(b"<second/>").data

    assert client.receive() == "<first/>"
    assert client.receive() == "<second/>"


def test_connection_closed_within_a_message_is_an_error():
    client = TCPClient("host", 700)
    client.socket = FakeSocket(b"<msg>cut</msg>")
    client.socket.data = client.socket.data[:-3]
    client.socket.close = lambda: None

    with pytest.raises(ConnectionException, match="Connection closed by server"):
        client.receive()

    assert client.socket is None


def test_length_shorter_than_its_own_header_is_an_error():
    client = TCPClient("host", 700)
    client.socket = FakeSocket(b"")
    client.socket.data = struct.pack('>L', 3)
    client.socket.close = lambda: None

    with pytest.raises(ConnectionException, match="Invalid message length 3"):
        client.receive()


class RecordingSocket:
    def __init__(self):
        self.sent = b""

    def sendall(self, data):
        self.sent += data


def test_length_counts_the_header_by_default():
    client = TCPClient("host", 700)
    client.socket = RecordingSocket()

    client.send("<a/>")

    assert client.socket.sent == struct.pack('>L', 8) + b"<a/>"


def test_payload_only_framing_counts_the_payload():
    client = TCPClient("host", 700, framing=LENGTH_OF_PAYLOAD)
    client.socket = RecordingSocket()

    client.send("<ä/>")

    assert client.socket.sent == struct.pack('>L', 5) + "<ä/>".encode("utf-8")


def test_payload_only_framing_reads_the_payload_length():
    client = TCPClient("host", 700, framing=LENGTH_OF_PAYLOAD)
    client.socket = FakeSocket(b"")
    client.socket.data = struct.pack('>L', 4) + b"<a/>" + struct.pack('>L', 0)

    assert client.receive() == "<a/>"
    assert client.receive() == ""


def test_unknown_framing_is_refused():
    with pytest.raises(ValueError):
        TCPClient("host", 700, framing="other")


def test_a_message_with_a_credential_is_not_printed(capsys):
    client = TCPClient("host", 700, framing=LENGTH_OF_PAYLOAD)
    client.socket = RecordingSocket()

    client.send("<password>secret</password>", loggable=False)

    assert "secret" not in capsys.readouterr().out
