import socket
import struct

class TCPClient:
    """
    A simple TCP client class.
    """

    def __init__(self, server_address, server_port):
        """
        Initializes the TCP client with server address and port.

        Args:
            server_address (str): The server's IP address or hostname.
            server_port (int): The server's port number.
        """
        self.server_address = server_address
        self.server_port = server_port
        self.socket = None

    def connect(self):
        """
        Connects to the server.
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_address, self.server_port))
            print(f"Connected to {self.server_address}:{self.server_port}")
        except Exception as e:
            print(f"Error connecting to server: {e}")
            self.socket = None

    def send(self, message):
        """
        Sends a message to the server.

        Args:
            message (str): The message to send.
        """
        if self.socket is None:
            self.connect()

        if self.socket is None:
            print("Connection failed. Cannot send message.")
            return

        try:
            payload = message.encode('utf-8')
            payload_length = len(payload)
            length_bytes = struct.pack('!I', payload_length)  # Pack length as big-endian unsigned integer

            self.socket.sendall(length_bytes)
            self.socket.sendall(payload)

            print(f"Sent message: {message}")

        except Exception as e:
            print(f"Error sending message: {e}")
            self.disconnect()

    def receive(self):
        """
        Receives a message from the server.
        """
        if self.socket is None:
            self.connect()

        if self.socket is None:
            print("Connection failed. Cannot receive message.")
            return None

        try:
            length_bytes = self.socket.recv(4)
            if not length_bytes:
                return None  # Connection closed by server

            payload_length = struct.unpack('!I', length_bytes)[0]
            payload = self.socket.recv(payload_length)
            message = payload.decode('utf-8')

            print(f"Received message: {message}")
            return message

        except Exception as e:
            print(f"Error receiving message: {e}")
            self.disconnect()
            return None

    def disconnect(self):
        """
        Disconnects from the server.
        """
        if self.socket:
            try:
                self.socket.close()
                print("Disconnected from server.")
            except Exception as e:
                print(f"Error disconnecting: {e}")
            finally:
                self.socket = None