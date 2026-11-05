import ssl
import subprocess

import pytest

from eppclient.tcpclient import TCPClient
from eppclient.tls import new_tls_context
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


def test_skip_verify_warns(caplog):
    new_tls_context(insecure_skip_verify=True)

    assert "rpp_epp_tls_insecure_skip_verify" in caplog.text


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
