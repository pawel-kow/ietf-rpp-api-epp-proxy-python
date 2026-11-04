import threading
import time
from concurrent.futures import ThreadPoolExecutor

from eppclient.eppclient import EPPClient

REPLY = (
    '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response>'
    '<result code="1000"><msg>{}</msg></result>'
    '</response></epp>'
)


class FakeTransport:
    """Answers in order like a real socket, slowly enough to expose interleaving."""

    def __init__(self):
        self.pending = []
        self.guard = threading.Lock()

    def send(self, message):
        with self.guard:
            self.pending.append(message)

    def receive(self):
        time.sleep(0.005)
        with self.guard:
            return REPLY.format(self.pending.pop(0))


def test_concurrent_commands_each_get_their_own_response():
    client = EPPClient("unused", 0, "user", "pw")
    client.client = FakeTransport()
    client._connected = True

    def command(i):
        return f"command-{i}", client.send_and_get_response(f"command-{i}")[2]

    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(command, range(40)))

    assert all(sent in received for sent, received in results)
