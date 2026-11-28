"""What the proxy prints of an RRI exchange that carries verification information (docs/rri/rri-extension.md, Security
Considerations): neither the command nor its reply reaches stdout, over a real TCP client."""
import socket
import struct
import threading

from core.model.contact.contact_replacement import ContactReplacement
from core.model.contact.address import Address
from core.model.contact.contacts import Contact, ContactType
from extensions.rri.core.model.contact_verifications import ContactVerifications
from extensions.rri.core.model.verification_information import VerificationInformation
from extensions.rri.core.ports.rri_gateways import EXTENSION_ID
from registry_adapter.common.transport.tcp_client import TCPClient
from registry_adapter.rri.gateways.rri_backend import RriBackend
from registry_adapter.rri.session.rri_client import RriClient
from tests.helper.fake_rri_client import reply
from tests.helper.profiles import RRI_PARTS, RRI_PROFILE
from tests.unit.test_rri_adapter import CONTACT_INFO, DOMAIN_INFO, NAME
from tests.unit.test_rri_verification_process import OWN

REFERENCE = "ABC123"       # in the reply of CONTACT_INFO and in the record of the create below


class ScriptedServer:
    """Answers each frame it reads with the next of its replies, on 127.0.0.1."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.listener = socket.create_server(("127.0.0.1", 0))
        self.listener.settimeout(5)
        self.port = self.listener.getsockname()[1]
        self.thread = threading.Thread(target=self._serve, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc_info):
        self.thread.join(5)
        self.listener.close()

    def _frame(self, connection) -> bytes:
        header = connection.recv(4)
        size = struct.unpack(">L", header)[0] - 4
        data = b""
        while len(data) < size:
            data += connection.recv(size - len(data))
        return data

    def _serve(self):
        try:
            connection, _ = self.listener.accept()
            with connection:
                connection.settimeout(5)
                for answer in self.replies:
                    self._frame(connection)
                    payload = answer.encode()
                    connection.sendall(struct.pack(">L", len(payload) + 4) + payload)
        except OSError:
            pass


def backend_over(port):
    client = RriClient(TCPClient("127.0.0.1", port), "DENIC-1000022-RRI", "pw")
    return RriBackend(client, RRI_PROFILE, extension_parts=RRI_PARTS), client


def verified_contact():
    record = VerificationInformation(claims=["name"], result="success", reference=REFERENCE, date="2023-11-11T15:36:21+02:00",
                                     evidence="idcard", method="auth", trust_framework="de_denic")
    return Contact(id="DENIC-1000022-HOLDER", type=ContactType.PERSON, name="Erika Mustermann", email=["erika@example.com"],
                   extensions={EXTENSION_ID: ContactVerifications(blocks=[record])})


def test_a_contact_create_with_records_and_the_reply_to_a_contact_info_are_not_printed(capsys):
    with ScriptedServer([reply(), reply(), CONTACT_INFO]) as server:
        gateway, client = backend_over(server.port)
        gateway.contacts.create(verified_contact())
        gateway.contacts.info("DENIC-1000022-HOLDER")
        client.disconnect(send_logout=False)

    out = capsys.readouterr().out
    assert "Sent message" in out and "Received message" in out      # the exchange is printed otherwise
    assert REFERENCE not in out and "Mustermann" not in out and "idcard" not in out


def test_an_update_that_carries_the_stored_records_over_is_not_printed(capsys):
    with ScriptedServer([reply(), CONTACT_INFO, reply()]) as server:
        gateway, client = backend_over(server.port)
        outcome = gateway.contacts.replace(ContactReplacement(
            id="DENIC-1000022-HOLDER", name="Erika Mustermann", email=["new@example.com"], phone=["+49.6912345678"],
            address=Address(street=["Musterweg 12"], city="Frankfurt am Main", postalCode="60596", country="DE"),
            unchanged=frozenset({"authInfo"})))
        client.disconnect(send_logout=False)

    out = capsys.readouterr().out
    assert not outcome.unchanged                        # the UPDATE was sent
    assert "<contact:update>" not in out and REFERENCE not in out and "new@example.com" not in out


def test_the_recursive_domain_info_of_the_verification_process_is_not_printed(capsys):
    with ScriptedServer([reply(), OWN]) as server:
        gateway, client = backend_over(server.port)
        process = gateway.extension(EXTENSION_ID).verification_processes.info(NAME).payload
        client.disconnect(send_logout=False)

    out = capsys.readouterr().out
    assert process.holders[0].verifications[0].reference == "REF-SECRET-1"
    assert "REF-SECRET-1" not in out and "DENIC-1000022-A" not in out


def test_the_exchange_of_a_command_without_verification_data_is_printed(capsys):
    with ScriptedServer([reply(), DOMAIN_INFO]) as server:
        gateway, client = backend_over(server.port)
        gateway.domains.info(NAME)
        client.disconnect(send_logout=False)

    assert NAME in capsys.readouterr().out
