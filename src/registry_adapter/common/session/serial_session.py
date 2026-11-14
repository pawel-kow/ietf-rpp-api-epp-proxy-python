import threading

from registry_adapter.common.transport.tcp_client import ConnectionException


class SerialSession:
    """One user's session with a registry over one transport, shared by all of that user's concurrent requests.

    A registry matches a reply to its command by order only, so a command and its reply must not interleave with any
    other traffic on the socket: `_lock` serializes every exchange. It is re-entrant because `connect()` and
    `disconnect()` log in and out through the same path. Before a command the transport is asked whether the server
    has closed the idle session, which is then opened again. A command is sent once more on a new session only when
    sending it failed, never when its reply was lost: the server may have run it.

    A subclass logs in (`_log_in`, after the transport connected; it raises when refused) and out (`_log_out`).
    """

    name = "registry"

    def __init__(self, transport):
        self.client = transport
        self._connected = False
        self._lock = threading.RLock()

    @property
    def connected(self) -> bool:
        return self._connected

    def _log_in(self):
        raise NotImplementedError

    def _log_out(self):
        raise NotImplementedError

    def connect(self):
        with self._lock:
            try:
                self.client.connect()
                self._log_in()
                self._connected = True
            except Exception as e:
                print(f"Error connecting to the {self.name} server: {e}")
                self._connected = False

    def disconnect(self, send_logout=True):
        with self._lock:
            try:
                try:
                    if send_logout:
                        self._log_out()
                finally:
                    self.client.disconnect()
                    self._connected = False
            except Exception as e:
                print(f"Error disconnecting from the {self.name} server: {e}")

    def _open_session(self):
        """Logs in unless there is a session. Callers must hold self._lock."""
        if not self._connected:
            self.connect()
        if not self._connected:
            raise ConnectionException(f"{self.name} server is not reachable")

    def _round_trip(self, message: str, loggable=True) -> str:
        """Sends a command on the session, opened or re-opened as needed, and answers the raw reply. `loggable` is
        False for a command that holds a secret, which is then not printed."""
        with self._lock:
            if self._connected and self.client.closed_by_peer():
                print(f"{self.name} session closed by the server, logging in again")
                self.disconnect(send_logout=False)
            self._open_session()
            try:
                self._write(message, loggable)
            except Exception:
                # A failed send leaves no complete command on the server, so sending it again on a new session
                # cannot run it twice.
                self._open_session()
                self._write(message, loggable)
            return self._read()

    def _exchange(self, message: str, loggable=True) -> str:
        """One exchange on the open socket, for the login and logout. Callers must hold self._lock."""
        self._write(message, loggable)
        return self._read()

    def _write(self, message: str, loggable=True):
        """Sends, and closes the session if that fails. Callers must hold self._lock."""
        try:
            if loggable:
                self.client.send(message)
            else:
                self.client.send(message, loggable=False)
        except Exception as e:
            print(f"Error sending to the {self.name} server: {e}")
            self.disconnect(send_logout=False)
            raise

    def _read(self) -> str:
        """Receives, and closes the session if that fails. Callers must hold self._lock."""
        try:
            return self.client.receive()
        except Exception as e:
            print(f"Error receiving from the {self.name} server: {e}")
            self.disconnect(send_logout=False)
            raise
