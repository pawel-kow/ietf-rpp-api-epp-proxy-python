import socket
import struct
import threading
import uuid
import re
import xml.etree.ElementTree as ET
from lxml import etree
from helpers import decode_xml
from .tcpclient import ConnectionException

EPP_NAMESPACE = {'epp': 'urn:ietf:params:xml:ns:epp-1.0'}
SEC_DNS_EXTENSION = "urn:ietf:params:xml:ns:secDNS-1.1"
LOGIN_EXTENSIONS = (SEC_DNS_EXTENSION,)

class EPPClient:
    """
    A simple EPP client class.

    One instance owns one EPP session and is shared by all concurrent requests of
    that user. EPP has no way to match a response to a command on the wire other
    than order, so a command and its response must not interleave with any other
    traffic on the socket: _lock serializes every exchange. It is re-entrant because
    connect() and disconnect() send login/logout through the same path.
    """

    def __init__(self, transport, username, password):
        """
        Initializes the EPP client with its transport and credentials.

        Args:
            transport: Provides connect(), send(message), receive() and disconnect().
            username (str): The EPP clID to log in with.
            password (str): The EPP password to log in with.
        """
        self.client = transport
        self.username = username
        self.password = password
        self._connected = False 
        self._server_extensions = frozenset()
        self._lock = threading.RLock()

    def connect(self):
        """
        Connects to the server.
        """
        with self._lock:
            try:
                self.client.connect()
                # Reading Hello message from server
                hello = self.client.receive()
                print("Hello from the server", hello)
                self._server_extensions = self._parse_greeting(hello)
                # Sending login message
                self._send_login(self.username, self.password)
                self._connected = True
            except Exception as e:
                print(f"Error connecting to server: {e}")
                self._connected = False

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
            if not self._connected:
                self.connect()
            return self._send_and_get_response(message)

    def _send_and_get_response(self, message: str) -> tuple[bool, str, str]:
        """
        Class internal method to send a message and receive a response.
        This method is used internally by the class to handle the sending and receiving of messages.
        It is not intended to be used directly by the user.
        Callers must hold self._lock.

        Args:
            message (str): The message to send.

        Returns:
            tuple[bool, str, str]: A tuple containing:
                - success (bool): Whether the operation was successful.
                - code (str): The EPP response code from the server.
                - response (str): The full response message from the server.
        """
        try:
            self.client.send(message)
        except Exception as e:
            print(f"Error sending message: {e}")
            self.disconnect(send_logout=False)
            raise

        try:
            response = self.client.receive()
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
            if not self._connected:
                self.connect()
            if not self._connected:
                raise ConnectionException("EPP server is not reachable")
            return uri in self._server_extensions

    def verify_credentials(self, user, password):
        return self.username == user and self.password == password

    @property
    def connected(self):
        return self._connected

    def disconnect(self, send_logout=True):
        """
        Disconnects from the server.
        """
        with self._lock:
            try:
                try:
                    # Sending logout message
                    if send_logout:
                        self._send_logout()
                finally:
                    #disconnect TCP connection
                    self.client.disconnect()
                    self._connected = False
            except Exception as e:
                print(f"Error disconnecting from server: {e}")

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
