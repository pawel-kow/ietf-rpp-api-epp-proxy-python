import struct

from eppclient.tcpclient import TCPClient


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


def test_receive_survives_a_message_that_is_not_utf8():
    client = TCPClient("host", 700)
    client.socket = FakeSocket("<msg>Jörg</msg>".encode("latin-1"))

    assert client.receive() == "<msg>J�rg</msg>"
