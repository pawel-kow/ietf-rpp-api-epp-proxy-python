import socket
import struct

class ConnectionException(Exception):
    pass

EPP_READ_TIMEOUT = 20  # seconds

class TCPClient:
    """
    A simple TCP client class.
    """

    def __init__(self, server_address, server_port, tls_context=None):
        """
        Initializes the TCP client with server address and port.

        Args:
            server_address (str): The server's IP address or hostname.
            server_port (int): The server's port number.
            tls_context (ssl.SSLContext): Connects over TLS if given, otherwise over
                plain TCP.
        """
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
            self.socket.settimeout(EPP_READ_TIMEOUT)  # Set a timeout for the connection
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

    def send(self, message):
        """
        Sends a message to the server.

        Args:
            message (str): The message to send.
        """
        if self.socket is None:
            self.connect()
        else:
            try:
                # Check if the socket is still alive by sending a zero-byte message
                self.socket.send(b'')
            except socket.error:
                print("TCPClient: Socket is dead.")
                raise

        if self.socket is None:
            print("TCPClient: Connection failed. Cannot send message.")
            return

        try:
            payload = message.encode('utf-8')
            payload_length = len(payload)
            length_bytes = struct.pack('>L', payload_length + 4)  # Pack length as big-endian unsigned integer

            self.socket.sendall(length_bytes)
            self.socket.sendall(payload)

            print(f"TCPClient: Sent message: {message}")

        except Exception as e:
            print(f"TCPClient: Error sending message: {e}")
            self.disconnect()
            raise

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
            if payload_length < 4:
                raise ConnectionException(f"Invalid message length {payload_length}")

            payload = self._recv_exact(payload_length - 4)  # Subtract 4 bytes for the length field
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