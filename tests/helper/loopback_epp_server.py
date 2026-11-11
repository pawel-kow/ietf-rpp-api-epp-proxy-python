import socket
import ssl
import struct
import threading


class LoopbackEppServer:
    """
    Answers one connection on 127.0.0.1 with one EPP frame, over TLS if given
    a PEM file holding a certificate and its key. With close_after_reply it then
    closes the connection, as a server does with an idle session, and otherwise
    waits for the client.
    """

    def __init__(self, payload: bytes, certificate: str | None = None, close_after_reply: bool = False):
        self.payload = payload
        self.close_after_reply = close_after_reply
        self.context = None
        if certificate:
            self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.context.load_cert_chain(certificate)
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

    def _serve(self):
        try:
            connection, _ = self.listener.accept()
            with connection:
                if self.context:
                    connection = self.context.wrap_socket(connection, server_side=True)
                connection.sendall(struct.pack('>L', len(self.payload) + 4) + self.payload)
                if self.close_after_reply:
                    if self.context:
                        connection.unwrap()  # Sends close_notify.
                    return
                # Wait for the client, so that closing cannot cut the reply short.
                connection.recv(1)
        except OSError:
            pass  # The tests of a rejected certificate fail the handshake here.
