import base64
import socket
import threading
import time

import pytest
import uvicorn

from app import create_app
from controller.epp_session_authenticator import EppSessionAuthenticator
from tests.helper.fake_epp_client import FakeEppClient

MEDIA_TYPE = "application/rpp+json"
CREDENTIALS = "Basic " + base64.b64encode(b"user:pw").decode()
HEADERS = {"Authorization": CREDENTIALS, "Accept": MEDIA_TYPE, "RPP-Cltrid": "cl-1", "Content-Type": MEDIA_TYPE}
EPP_OK = (True, "1000", (
    '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response><result code="1000"><msg>Message</msg></result>'
    '<trID><clTRID>cl-1</clTRID><svTRID>sv-1</svTRID></trID></response></epp>'
))

# Core §16.1.4: DELETE MUST reject content. One route of each kind.
DELETES = [
    "/contacts/FO-1",
    "/domainNames/foo.example",
    "/hosts/ns1.foo.example",
    "/contacts/FO-1/processes/transferProcesses/latest",
    "/domainNames/foo.example/processes/transferProcesses/latest",
]
BODIES = [b"{}", b"null", b"[]", b"0", b"false", b'""', b" ", b"\n", b"{bad"]


def setup():
    clients = []

    def factory(username, password):
        clients.append(FakeEppClient(username, password, reply=EPP_OK))
        return clients[-1]

    return create_app(EppSessionAuthenticator(factory)), clients


def sent_any(clients):
    return any(client.sent for client in clients)


@pytest.mark.parametrize("url", DELETES)
@pytest.mark.parametrize("body", BODIES)
def test_delete_with_a_body_is_a_400_without_epp(url, body):
    app, clients = setup()
    response = app.test_client().request("DELETE", url, content=body, headers=HEADERS)
    assert response.status_code == 400
    assert response.headers["RPP-Code"] == "02001"
    assert not sent_any(clients)


@pytest.mark.parametrize("url", DELETES)
def test_delete_with_a_form_body_is_a_400_without_epp(url):
    app, clients = setup()
    headers = {k: v for k, v in HEADERS.items() if k != "Content-Type"}
    response = app.test_client().request("DELETE", url, data={"a": "b"}, headers=headers)
    assert response.status_code == 400
    assert not sent_any(clients)


@pytest.mark.parametrize("url", DELETES)
def test_delete_without_a_body_is_not_rejected(url):
    app, clients = setup()
    headers = {k: v for k, v in HEADERS.items() if k != "Content-Type"}
    response = app.test_client().delete(url, headers=headers)
    assert response.status_code != 400


class LiveServer:
    """The app under uvicorn on 127.0.0.1, as in production, for requests whose body comes late."""

    def __init__(self, app):
        self.listener = socket.create_server(("127.0.0.1", 0))
        self.port = self.listener.getsockname()[1]
        self.server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
        self.thread = threading.Thread(target=self.server.run, kwargs={"sockets": [self.listener]}, daemon=True)

    def __enter__(self):
        self.thread.start()
        deadline = time.time() + 10
        while not self.server.started and time.time() < deadline:
            time.sleep(0.02)
        return self

    def __exit__(self, *exc_info):
        self.server.should_exit = True
        self.thread.join(10)
        self.listener.close()

    def request(self, method, path, body, delay=0.3, timeout=5):
        """Sends the headers, waits, then sends the body. Returns the status line, or None on a timeout."""
        lines = [f"{method} {path} HTTP/1.1", f"Host: 127.0.0.1:{self.port}", f"Authorization: {CREDENTIALS}",
                 f"Accept: {MEDIA_TYPE}", "RPP-Cltrid: cl-1", f"Content-Type: {MEDIA_TYPE}",
                 f"Content-Length: {len(body)}", "Connection: close"]
        with socket.create_connection(("127.0.0.1", self.port), timeout=timeout) as connection:
            connection.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())
            time.sleep(delay)
            connection.sendall(body)
            try:
                reply = b""
                while b"\r\n" not in reply:
                    chunk = connection.recv(4096)
                    if not chunk:
                        break
                    reply += chunk
            except socket.timeout:
                return None
        return reply.split(b"\r\n")[0].decode()


@pytest.mark.parametrize("path,body,status", [
    ("/domainNames/foo.example", b"{}", "400"),
    ("/contacts/FO-1/processes/transferProcesses/latest", b"{}", "400"),
    ("/contacts/FO-1/processes/transferProcesses/latest/transferApprove", b'{"@type": "transferProcess"}', "202"),
    ("/domainNames/foo.example/processes/transferProcesses/latest/transferApprove", b'{"@type": "domainTransferProcess"}', "202"),
])
def test_a_body_that_arrives_after_the_headers_does_not_hang(path, body, status):
    app, clients = setup()
    method = "DELETE" if "Approve" not in path else "POST"
    with LiveServer(app) as server:
        for _ in range(3):
            line = server.request(method, path, body)
            assert line is not None, "the request hung"
            assert f" {status} " in line
