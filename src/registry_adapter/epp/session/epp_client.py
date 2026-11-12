import re
import socket
import struct
import uuid
import xml.etree.ElementTree as ET

from lxml import etree

from registry_adapter.common.session.serial_session import SerialSession
from registry_adapter.common.xmlsafe.xml_helper import decode_xml

EPP_NAMESPACE = {'epp': 'urn:ietf:params:xml:ns:epp-1.0'}

SEC_DNS_EXTENSION = "urn:ietf:params:xml:ns:secDNS-1.1"

IDN_EXTENSION = "urn:ietf:params:xml:ns:idn-1.0"

RGP_EXTENSION = "urn:ietf:params:xml:ns:rgp-1.0"

LOGIN_EXTENSIONS = (SEC_DNS_EXTENSION, IDN_EXTENSION, RGP_EXTENSION)

class EPPClient(SerialSession):
    """
    A simple EPP client class.

    One instance owns one EPP session and is shared by all concurrent requests of that user; `SerialSession` keeps
    every exchange apart, opens the session again when the server closed it, and resends only a command that was
    never written. EPP begins with the server's greeting, whose extensions `supports_extension` answers from.
    """

    name = "EPP"

    def __init__(self, transport, username, password):
        """
        Initializes the EPP client with its transport and credentials.

        Args:
            transport: Provides connect(), send(message), receive() and disconnect().
            username (str): The EPP clID to log in with.
            password (str): The EPP password to log in with.
        """
        super().__init__(transport)
        self.username = username
        self.password = password
        self._server_extensions = frozenset()

    def _log_in(self):
        """Reads the greeting and logs in."""
        hello = self.client.receive()
        print("Hello from the server", hello)
        self._server_extensions = self._parse_greeting(hello)
        self._send_login(self.username, self.password)

    def _log_out(self):
        self._send_logout()

    def send_and_get_response(self, message: str) -> tuple[bool, str, str]:
        """
        Sends a message to the server and receives a response.

        Args:
            message (str): The message to send.

        Returns:
            tuple[bool, str, str]: A tuple containing:
                - success (bool): Whether the operation was successful.
                - code (str): The EPP response code from the server.
                - response (str): The full response message from the server.
        """
        with self._lock:
            return self._parsed(self._round_trip(message))

    def _send_and_get_response(self, message: str) -> tuple[bool, str, str]:
        """Sends a message on the open socket and receives its response. Callers must hold self._lock."""
        return self._parsed(self._exchange(message))

    def _parsed(self, response: str) -> tuple[bool, str, str]:
        """The result of a response, which closes the session if it cannot be read. Callers must hold self._lock."""
        try:
            print(f"Received response: {response}")
            success, code, msg = self._parse_epp_response(response)
            if not success:
                print(f"EPP Command failed: {code} - {msg}")
            return success, code, response
        except Exception as e:
            print(f"Error receiving response: {e}")
            self.disconnect(send_logout=False)
            raise

    def supports_extension(self, uri: str) -> bool:
        """Whether the server offers an extension, which only its greeting says."""
        with self._lock:
            self._open_session()
            return uri in self._server_extensions

    def verify_credentials(self, user, password):
        return self.username == user and self.password == password

    def _send_login(self, username, password):
        """
        Sends a login message to the server.

        Args:
            username (str): The username to login with.
            password (str): The password to login with.
        """
        login_message = f"""<?xml version="1.0"?>
<epp xmlns="urn:ietf:params:xml:ns:epp-1.0">
  <command>
    <login>
      <clID>{username}</clID>
      <pw>{password}</pw>
      <options>
        <version>1.0</version>
        <lang>en</lang>
      </options>
      <svcs>
        <objURI>urn:ietf:params:xml:ns:domain-1.0</objURI>
        <objURI>urn:ietf:params:xml:ns:host-1.0</objURI>
        <objURI>urn:ietf:params:xml:ns:contact-1.0</objURI>
        {self._login_service_extension()}
      </svcs>
    </login>
    <clTRID>{uuid.uuid4()}</clTRID>
  </command>
</epp>
"""
        response = self._send_and_get_response(login_message)
        success, code, msg = self._parse_epp_response(response[2])
        if not success:
            raise Exception(f"Login failed: {msg}")

    def _login_service_extension(self) -> str:
        """What the proxy uses and the server offers. The element may not be empty."""
        uris = [uri for uri in LOGIN_EXTENSIONS if uri in self._server_extensions]
        if not uris:
            return ""
        return "<svcExtension>" + "".join(f"<extURI>{uri}</extURI>" for uri in uris) + "</svcExtension>"

    def _send_logout(self):
        """
        Sends a logout message to the server.
        """
        logout_message = f"""<?xml version="1.0" standalone="no"?>
<epp xmlns="urn:ietf:params:xml:ns:epp-1.0">
  <command>
    <logout/>
    <clTRID>{uuid.uuid4()}</clTRID>
  </command>
</epp>"""
        response = self._send_and_get_response(logout_message)
        success, code, msg = self._parse_epp_response(response[2])
        if not success:
            raise Exception(f"Logout failed: {msg}")

    def _parse_greeting(self, greeting: str) -> frozenset[str]:
        path = "./epp:greeting/epp:svcMenu/epp:svcExtension/epp:extURI"
        return frozenset((uri.text or "").strip() for uri in decode_xml(greeting).findall(path, namespaces=EPP_NAMESPACE))

    def _parse_epp_response(self, response):
        """
        Parses an EPP response.

        Args:
            response (str): The response to parse.
        """
        root = decode_xml(response)
        code = root.find("./epp:response/epp:result", namespaces=EPP_NAMESPACE).attrib.get("code")
        msg = root.find("./epp:response/epp:result/epp:msg", namespaces=EPP_NAMESPACE).text
        if re.match(r"1[0-9]{3}", code):
            return True, code, msg
        else:
            return False, code, msg
