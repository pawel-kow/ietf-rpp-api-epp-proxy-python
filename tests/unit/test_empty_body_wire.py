import base64
import socket
import threading
import time

import pytest
import uvicorn

from core.session.session_pool import SessionPool
from registry_adapter.epp.profile import EPP_PROFILE
from rpp.http.app import create_app
from tests.helper.epp_backends import epp_backends
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

    return create_app(SessionPool(epp_backends(factory)), EPP_PROFILE), clients


@pytest.fixture(scope="module")
def shared():
    """One app for the module: building it from the OpenAPI takes seconds. Tests clear `clients`."""
    return setup()


def forget(clients):
    """The session pool keeps one session per user, so keep the client and clear what it recorded."""
    for client in clients:
        client.sent.clear()


def sent_any(clients):
    return any(client.sent for client in clients)


@pytest.mark.parametrize("url", DELETES)
@pytest.mark.parametrize("body", BODIES)
def test_delete_with_a_body_is_a_400_without_epp(shared, url, body):
    app, clients = shared
    forget(clients)
    response = app.test_client().request("DELETE", url, content=body, headers=HEADERS)
    assert response.status_code == 400
    assert response.headers["RPP-Code"] == "02001"
    assert not sent_any(clients)


@pytest.mark.parametrize("url", DELETES)
def test_delete_with_a_form_body_is_a_400_without_epp(shared, url):
    app, clients = shared
    forget(clients)
    headers = {k: v for k, v in HEADERS.items() if k != "Content-Type"}
    response = app.test_client().request("DELETE", url, data={"a": "b"}, headers=headers)
    assert response.status_code == 400
    assert not sent_any(clients)


@pytest.mark.parametrize("url", DELETES)
def test_delete_without_a_body_is_not_rejected(shared, url):
    app, clients = shared
    forget(clients)
    headers = {k: v for k, v in HEADERS.items() if k != "Content-Type"}
    response = app.test_client().delete(url, headers=headers)
    assert response.status_code == (200 if "processes" not in url else 202)


class LiveServer:
    """The app under uvicorn on 127.0.0.1, as in production, for requests with a late or chunked body."""

    def __init__(self, app):
        self.listener = socket.create_server(("127.0.0.1", 0))
        self.port = self.listener.getsockname()[1]
        self.server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
        self.server.force_exit = True
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

    def request(self, method, path, body, content_type=MEDIA_TYPE, chunked=False, delay=0.3, timeout=5):
        """Sends the headers, waits, then sends the body. Returns the status line, or None on a timeout."""
        lines = [f"{method} {path} HTTP/1.1", f"Host: 127.0.0.1:{self.port}", f"Authorization: {CREDENTIALS}",
                 f"Accept: {MEDIA_TYPE}", "RPP-Cltrid: cl-1", "Connection: close"]
        if content_type:
            lines.append(f"Content-Type: {content_type}")
        lines.append("Transfer-Encoding: chunked" if chunked else f"Content-Length: {len(body)}")
        with socket.create_connection(("127.0.0.1", self.port), timeout=timeout) as connection:
            connection.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())
            time.sleep(delay)
            try:
                if chunked:
                    if body:
                        connection.sendall(f"{len(body):x}\r\n".encode() + body + b"\r\n")
                    connection.sendall(b"0\r\n\r\n")
                else:
                    connection.sendall(body)
            except (BrokenPipeError, ConnectionResetError):
                pass  # the server answered before the end of the body
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


CONTACT_LATEST = "/contacts/FO-1/processes/transferProcesses/latest"
DOMAIN_LATEST = "/domainNames/foo.example/processes/transferProcesses/latest"
URLENCODED = "application/x-www-form-urlencoded"
BOUNDARY = "xyz"
MULTIPART = f"multipart/form-data; boundary={BOUNDARY}"
FIELD = f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="a"\r\n\r\n1\r\n--{BOUNDARY}--\r\n'.encode()
FILE = (f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="f"; filename="f.txt"\r\n'
        f'Content-Type: text/plain\r\n\r\nhello\r\n--{BOUNDARY}--\r\n').encode()
FORMS = [
    (URLENCODED, b"a=1"), (URLENCODED, b"="), (URLENCODED, b"a"), (URLENCODED, b"&"),
    (MULTIPART, FIELD), (MULTIPART, FILE), (MULTIPART, b"garbage"),
]


def live_cases():
    """(id, method, path, body, content_type, status): content the proxy must see before it sends to EPP."""
    approve = {"contact": f"{CONTACT_LATEST}/transferApprove", "domain": f"{DOMAIN_LATEST}/transferApprove"}
    reject = {"contact": f"{CONTACT_LATEST}/transferReject", "domain": f"{DOMAIN_LATEST}/transferReject"}
    cancel = {"contact": CONTACT_LATEST, "domain": DOMAIN_LATEST}
    types = {"contact": "transferProcess", "domain": "domainTransferProcess"}
    create = {"contact": CONTACT_LATEST.rsplit("/", 1)[0], "domain": DOMAIN_LATEST.rsplit("/", 1)[0]}
    cases = []
    for kind in ("contact", "domain"):
        type_only = ('{"@type": "%s"}' % types[kind]).encode()
        create_body = ('{"@type": "%s", "transferDir": "pull"}' % types[kind]).encode()
        with_reason = ('{"@type": "%s", "reason": "ok"}' % types[kind]).encode()
        cases += [
            (f"{kind}-create", "POST", create[kind], create_body, MEDIA_TYPE, 202),
            (f"{kind}-approve-reason", "POST", approve[kind], with_reason, MEDIA_TYPE, 501),
            (f"{kind}-approve-unknown", "POST", approve[kind], b'{"x": 1}', MEDIA_TYPE, 400),
            (f"{kind}-approve-null", "POST", approve[kind], b"null", MEDIA_TYPE, 400),
            (f"{kind}-approve-type-only", "POST", approve[kind], type_only, MEDIA_TYPE, 202),
            (f"{kind}-approve-empty", "POST", approve[kind], b"", None, 202),
            (f"{kind}-cancel-json", "DELETE", cancel[kind], b"{}", MEDIA_TYPE, 400),
            (f"{kind}-cancel-empty", "DELETE", cancel[kind], b"", None, 202),
            (f"{kind}-reject-reason", "POST", reject[kind], with_reason, MEDIA_TYPE, 501),
            (f"{kind}-reject-type-only", "POST", reject[kind], type_only, MEDIA_TYPE, 202),
            (f"{kind}-reject-empty", "POST", reject[kind], b"", None, 202),
        ]
        for n, (content_type, body) in enumerate(FORMS):
            cases.append((f"{kind}-approve-form{n}", "POST", approve[kind], body, content_type, 400))
            cases.append((f"{kind}-cancel-form{n}", "DELETE", cancel[kind], body, content_type, 400))
            cases.append((f"{kind}-reject-form{n}", "POST", reject[kind], body, content_type, (400, 415)))
    return cases


@pytest.fixture(scope="module")
def live(shared):
    """One server for the module: starting and stopping uvicorn costs about a second each."""
    app, clients = shared
    with LiveServer(app) as server:
        yield server, clients


@pytest.mark.parametrize("chunked", [False, True], ids=["length", "chunked"])
@pytest.mark.parametrize("case", live_cases(), ids=lambda case: case[0] if isinstance(case, tuple) else None)
def test_content_is_seen_whatever_its_framing(live, case, chunked):
    """An approve, cancel or reject that is not valid never reaches EPP, as it does not through the test client."""
    _, method, path, body, content_type, status = case
    server, clients = live
    forget(clients)
    line = server.request(method, path, body, content_type, chunked, delay=0)
    assert line is not None, "the request hung"
    expected = status if isinstance(status, tuple) else (status,)
    assert any(f" {code} " in line for code in expected), line
    if max(expected) >= 400:
        assert not sent_any(clients)


@pytest.mark.parametrize("path,body,status", [
    ("/domainNames/foo.example", b"{}", "400"),
    ("/contacts/FO-1/processes/transferProcesses/latest", b"{}", "400"),
    ("/contacts/FO-1/processes/transferProcesses/latest/transferApprove", b'{"@type": "transferProcess"}', "202"),
    ("/domainNames/foo.example/processes/transferProcesses/latest/transferApprove", b'{"@type": "domainTransferProcess"}', "202"),
])
def test_a_body_that_arrives_after_the_headers_does_not_hang(live, path, body, status):
    server, _ = live
    method = "DELETE" if "Approve" not in path else "POST"
    for _ in range(3):
        line = server.request(method, path, body)
        assert line is not None, "the request hung"
        assert f" {status} " in line


def abort_cases():
    cases = []
    for kind, type_name in (("contact", "transferProcess"), ("domain", "domainTransferProcess")):
        latest = CONTACT_LATEST if kind == "contact" else DOMAIN_LATEST
        for op, method, path in (("approve", "POST", f"{latest}/transferApprove"),
                                 ("cancel", "DELETE", latest),
                                 ("reject", "POST", f"{latest}/transferReject")):
            cases.append((f"{kind}-{op}", method, path, ('{"@type": "%s"}' % type_name).encode()))
    return cases


def abort(server, method, path, body, mode):
    """Sends part of a request and closes the connection."""
    lines = [f"{method} {path} HTTP/1.1", f"Host: 127.0.0.1:{server.port}", f"Authorization: {CREDENTIALS}",
             f"Accept: {MEDIA_TYPE}", "RPP-Cltrid: cl-1", f"Content-Type: {MEDIA_TYPE}"]
    if mode == "short":
        lines.append("Content-Length: 200")
    else:
        lines.append("Transfer-Encoding: chunked")
    with socket.create_connection(("127.0.0.1", server.port), timeout=5) as connection:
        connection.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())
        if mode == "short":
            connection.sendall(body)
        elif mode == "unterminated":
            connection.sendall(f"{len(body):x}\r\n".encode() + body + b"\r\n")
    time.sleep(0.3)  # the server sees the disconnect, and would run the command if it took it for the end


@pytest.mark.parametrize("mode", ["short", "headers-only", "unterminated"])
@pytest.mark.parametrize("case", abort_cases(), ids=lambda case: case[0] if isinstance(case, tuple) else None)
def test_an_aborted_upload_runs_nothing(live, case, mode):
    """An approve cannot be undone, so a request that did not arrive whole is dropped."""
    _, method, path, body = case
    server, clients = live
    forget(clients)
    abort(server, method, path, body, mode)
    assert not sent_any(clients)
    forget(clients)


def test_an_unauthenticated_request_gets_its_401_before_its_body(live):
    """Security runs before the body is buffered, so an anonymous client cannot make the proxy wait for one."""
    server, clients = live
    forget(clients)
    lines = [f"POST {CONTACT_LATEST}/transferApprove HTTP/1.1", f"Host: 127.0.0.1:{server.port}",
             f"Accept: {MEDIA_TYPE}", "RPP-Cltrid: cl-1", f"Content-Type: {MEDIA_TYPE}", "Content-Length: 1000",
             "Connection: close"]
    with socket.create_connection(("127.0.0.1", server.port), timeout=3) as connection:
        connection.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())  # and no body
        reply = connection.recv(4096)
    assert reply.split(b"\r\n")[0] == b"HTTP/1.1 401 Unauthorized"
    assert not sent_any(clients)
