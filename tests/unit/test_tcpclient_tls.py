import ssl
import subprocess
import time

import pytest

from registry_adapter.common.transport.tcp_client import TCPClient
from registry_adapter.common.transport.tls import new_tls_context
from tests.helper.loopback_epp_server import LoopbackEppServer


@pytest.fixture(scope="session")
def localhost_certificate(tmp_path_factory):
    """A self-signed certificate naming only localhost, and its key, in one PEM file."""
    directory = tmp_path_factory.mktemp("tls")
    key, certificate, pem = (directory / name for name in ("key.pem", "cert.pem", "localhost.pem"))
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
         "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost",
         "-keyout", str(key), "-out", str(certificate)],
        check=True, capture_output=True,
    )
    pem.write_bytes(certificate.read_bytes() + key.read_bytes())
    return str(pem)


def trusting(certificate):
    context = new_tls_context(insecure_skip_verify=False)
    context.load_verify_locations(certificate)
    return context


def test_verification_is_on_by_default():
    context = new_tls_context(insecure_skip_verify=False)

    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_skip_verify_turns_off_certificate_and_hostname_check():
    context = new_tls_context(insecure_skip_verify=True)

    assert context.verify_mode == ssl.CERT_NONE
    assert context.check_hostname is False


def test_verification_on_does_not_warn(caplog):
    new_tls_context(insecure_skip_verify=False)

    assert caplog.text == ""


@pytest.mark.parametrize("insecure_skip_verify", [False, True])
def test_tls_1_2_is_the_minimum(insecure_skip_verify):
    context = new_tls_context(insecure_skip_verify=insecure_skip_verify)

    assert context.minimum_version == ssl.TLSVersion.TLSv1_2


def test_self_signed_certificate_is_rejected_by_default(localhost_certificate):
    with LoopbackEppServer(b"<greeting/>", localhost_certificate) as server:
        client = TCPClient("localhost", server.port, new_tls_context(insecure_skip_verify=False))

        with pytest.raises(ssl.SSLCertVerificationError):
            client.connect()


def test_failed_handshake_leaves_no_socket(localhost_certificate):
    with LoopbackEppServer(b"<greeting/>", localhost_certificate) as server:
        client = TCPClient("localhost", server.port, new_tls_context(insecure_skip_verify=False))

        with pytest.raises(ssl.SSLError):
            client.connect()

    assert client.socket is None


def test_trusted_certificate_with_the_right_name_connects(localhost_certificate):
    with LoopbackEppServer(b"<greeting/>", localhost_certificate) as server:
        client = TCPClient("localhost", server.port, trusting(localhost_certificate))
        client.connect()

        assert client.receive() == "<greeting/>"
        client.disconnect()


def test_trusted_certificate_with_another_name_is_rejected(localhost_certificate):
    with LoopbackEppServer(b"<greeting/>", localhost_certificate) as server:
        # The certificate names only "localhost".
        client = TCPClient("127.0.0.1", server.port, trusting(localhost_certificate))

        with pytest.raises(ssl.SSLCertVerificationError):
            client.connect()


def test_skip_verify_accepts_a_self_signed_certificate_with_another_name(localhost_certificate):
    with LoopbackEppServer(b"<greeting/>", localhost_certificate) as server:
        client = TCPClient("127.0.0.1", server.port, new_tls_context(insecure_skip_verify=True))
        client.connect()

        assert client.receive() == "<greeting/>"
        client.disconnect()


def test_reply_larger_than_one_tls_record_arrives_whole(localhost_certificate):
    payload = b"<msg>" + b"x" * 100_000 + b"</msg>"

    with LoopbackEppServer(payload, localhost_certificate) as server:
        client = TCPClient("127.0.0.1", server.port, new_tls_context(insecure_skip_verify=True))
        client.connect()

        assert client.receive() == payload.decode()
        client.disconnect()


def test_without_a_tls_context_the_connection_is_plain():
    with LoopbackEppServer(b"<greeting/>") as server:
        client = TCPClient("127.0.0.1", server.port)
        client.connect()

        assert not isinstance(client.socket, ssl.SSLSocket)
        assert client.receive() == "<greeting/>"
        client.disconnect()


def closed_by_peer_within(client, seconds=5):
    """The close reaches the client asynchronously, so it is polled for."""
    deadline = time.monotonic() + seconds
    while not client.closed_by_peer():
        if time.monotonic() > deadline:
            return False
        time.sleep(0.01)
    return True


@pytest.mark.parametrize("tls", [False, True])
def test_an_idle_open_connection_is_not_closed_by_peer(localhost_certificate, tls):
    with LoopbackEppServer(b"<greeting/>", localhost_certificate if tls else None) as server:
        client = TCPClient("127.0.0.1", server.port, new_tls_context(insecure_skip_verify=True) if tls else None)
        client.connect()
        client.receive()

        assert client.closed_by_peer() is False
        client.disconnect()


@pytest.mark.parametrize("tls", [False, True])
def test_a_connection_the_server_closed_is_closed_by_peer(localhost_certificate, tls):
    certificate = localhost_certificate if tls else None
    with LoopbackEppServer(b"<greeting/>", certificate, close_after_reply=True) as server:
        client = TCPClient("127.0.0.1", server.port, new_tls_context(insecure_skip_verify=True) if tls else None)
        client.connect()
        client.receive()

        assert closed_by_peer_within(client)
        client.disconnect()


def test_without_a_socket_the_connection_is_closed_by_peer():
    assert TCPClient("127.0.0.1", 700).closed_by_peer() is True
