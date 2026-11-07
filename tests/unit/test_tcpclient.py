import struct

import pytest

from eppclient.tcpclient import ConnectionException, TCPClient


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
