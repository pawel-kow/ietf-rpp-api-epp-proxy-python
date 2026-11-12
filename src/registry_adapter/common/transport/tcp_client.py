import select
import socket
import ssl
import struct

class ConnectionException(Exception):
    pass

READ_TIMEOUT = 20  # seconds

# What the 4-byte length prefix of a frame counts: the prefix and the payload (RFC 5734 §4), or the payload alone.
LENGTH_INCLUDES_HEADER = "includes-header"
LENGTH_OF_PAYLOAD = "payload-only"
HEADER_SIZE = 4

class TCPClient:
    """
    A simple TCP client class.
    """

    def __init__(self, server_address, server_port, tls_context=None, framing=LENGTH_INCLUDES_HEADER):
        """
        Initializes the TCP client with server address and port.

        Args:
            server_address (str): The server's IP address or hostname.
            server_port (int): The server's port number.
            tls_context (ssl.SSLContext): Connects over TLS if given, otherwise over
                plain TCP.
            framing (str): What the length prefix of a frame counts, LENGTH_INCLUDES_HEADER or LENGTH_OF_PAYLOAD.
        """
        if framing not in (LENGTH_INCLUDES_HEADER, LENGTH_OF_PAYLOAD):
            raise ValueError(f"Unknown framing {framing!r}")
        self._length_offset = HEADER_SIZE if framing == LENGTH_INCLUDES_HEADER else 0
        self.server_address = server_address
        self.server_port = server_port
        self.tls_context = tls_context
        self.socket = None

    def connect(self):
        """
        Connects to the server.
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(READ_TIMEOUT)  # Set a timeout for the connection
            self.socket.connect((self.server_address, self.server_port))
            if self.tls_context:
                self.socket = self.tls_context.wrap_socket(
                    self.socket, server_hostname=self.server_address)
            print(f"TCPClient: Connected to {self.server_address}:{self.server_port}")
        except Exception as e:
            print(f"Error connecting to server: {e}")
            if self.socket:
                self.socket.close()
            self.socket = None
            raise

    def send(self, message, loggable=True):
        """
        Sends a message to the server.

        Args:
            message (str): The message to send.
            loggable (bool): False for a message that holds a credential, which is then not printed.
        """
        if self.socket is None:
            self.connect()

        if self.socket is None:
            print("TCPClient: Connection failed. Cannot send message.")
            return

        try:
            payload = message.encode('utf-8')
            payload_length = len(payload)
            length_bytes = struct.pack('>L', payload_length + self._length_offset)  # big-endian unsigned integer

            self.socket.sendall(length_bytes)
            self.socket.sendall(payload)

            print(f"TCPClient: Sent message: {message if loggable else '(not logged: it holds a credential)'}")

        except Exception as e:
            print(f"TCPClient: Error sending message: {e}")
            self.disconnect()
            raise

    def closed_by_peer(self) -> bool:
        """
        Whether an idle connection is over. The registry protocols send nothing unasked, so between
        exchanges anything readable is the server closing it (EOF, TLS close_notify)
        or a reply to no command, such as a 2500 before it closes.
        """
        if self.socket is None:
            return True
        if isinstance(self.socket, ssl.SSLSocket) and self.socket.pending():
            return True
        readable, _, _ = select.select([self.socket], [], [], 0)
        return bool(readable)

    def receive(self):
        """
        Receives a message from the server.
        """
        if self.socket is None:
            self.connect()

        if self.socket is None:
            print("TCPClient: Connection failed. Cannot receive message.")
            raise ConnectionException("TCPClient: Connection failed. Cannot receive message.")

        try:
            length_bytes = self._recv_exact(4)
            payload_length = struct.unpack('>L', length_bytes)[0]
            if payload_length < self._length_offset:
                raise ConnectionException(f"Invalid message length {payload_length}")

            payload = self._recv_exact(payload_length - self._length_offset)
            message = payload.decode('utf-8')

            print(f"TCPClient: Received message: {message}")
            return message

        except Exception as e:
            print(f"TCPClient: Error receiving message: {e}")
            self.disconnect()
            raise ConnectionException(f"TCPClient: Error receiving message: {e}")

    def _recv_exact(self, size):
        """
        Reads exactly size bytes. One recv() may return less, over TLS at most one record.

        Args:
            size (int): The number of bytes to read.
        """
        data = bytearray()
        while len(data) < size:
            chunk = self.socket.recv(size - len(data))
            if not chunk:
                raise ConnectionException("TCPClient: Connection closed by server")
            data += chunk
        return bytes(data)

    def disconnect(self):
        """
        Disconnects from the server.
        """
        if self.socket:
            try:
                self.socket.close()
                print("TCPClient: Disconnected from server.")
            except Exception as e:
                raise ConnectionException(f"TCPClient: error disconnecting {e}")
            finally:
                self.socket = None