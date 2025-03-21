import socket
import struct
from .tcpclient import TCPClient
import uuid
import xml.etree.ElementTree as ET
from lxml import etree
from helpers import decode_xml

class EPPClient:
    """
    A simple EPP client class.
    """

    def __init__(self, server_address, server_port, username, password):
        """
        Initializes the EPP client with server address and port.

        Args:
            server_address (str): The server's IP address or hostname.
            server_port (int): The server's port number.
        """
        self.client = TCPClient(server_address, server_port)
        self.username = username
        self.password = password
        self._connected = False 

    def connect(self):
        """
        Connects to the server.
        """
        try:
            self.client.connect()
            # Reading Hello message from server
            hello = self.client.receive()
            print("Hello from the server", hello)
            # Sending login message
            self._send_login(self.username, self.password)
            self._connected = True
        except Exception as e:
            print(f"Error connecting to server: {e}")
            self._connected = False

    def send_and_get_response(self, message):
        if not self._connected:
            self.connect()
        return self._send_and_get_response(message)

    def _send_and_get_response(self, message):
        """
        Sends a message to the server.

        Args:
            message (str): The message to send.
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
                raise Exception(f"EPP Command failed: {code} - {msg}")
            return response
        except Exception as e:
            print(f"Error receiving response: {e}")
            self.disconnect(send_logout=False)
            raise


    def disconnect(self, send_logout=True):
        """
        Disconnects from the server.
        """
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
        <svcExtension>
          <extURI>urn:ietf:params:xml:ns:secDNS-1.1</extURI>
        </svcExtension>
      </svcs>
    </login>
    <clTRID>{uuid.uuid4()}</clTRID>
  </command>
</epp>
"""
        response = self._send_and_get_response(login_message)
        success, code, msg = self._parse_epp_response(response)
        if not success:
            raise Exception(f"Login failed: {msg}")

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
        success, code, msg = self._parse_epp_response(response)
        if not success:
            raise Exception(f"Logout failed: {msg}")

    def _parse_epp_response(self, response):
        """
        Parses an EPP response.

        Args:
            response (str): The response to parse.
        """
        root = decode_xml(response)
        namespace = {'epp': 'urn:ietf:params:xml:ns:epp-1.0'}

        code = root.find("./epp:response/epp:result", namespaces=namespace).attrib.get("code")
        msg = root.find("./epp:response/epp:result/epp:msg", namespaces=namespace).text
        if code == "1000":
            return True, code, msg
        else:
            return False, code, msg
