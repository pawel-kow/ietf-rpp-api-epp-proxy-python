from registry_adapter.common.session.serial_session import SerialSession
from registry_adapter.rri.xml.codec import rri_to_str, str_to_rri
from registry_adapter.rri.xml.generated.global_5_0 import LoginType, LogoutType, RegistryRequest, RegistryResponse
from registry_adapter.rri.xml.generated.transaction_5_0 import ResultType


class RriLoginError(Exception):
    """The server refused the LOGIN. Holds its message codes, never the credentials."""


class RriClient(SerialSession):
    """One RRI session (DENIC RRI 5.0, XML). RRI has no greeting: LOGIN is the first request, and is not printed, as
    it holds the password. The server closes a session after 5 minutes without a request, and the session is opened
    again before the next command. RRI commands are not idempotent, which the retry rule of `SerialSession` keeps.
    """

    name = "RRI"

    def __init__(self, transport, username: str, password: str):
        super().__init__(transport)
        self.username = username
        self.password = password

    @property
    def regacc_id(self) -> str:
        """The RegAccId the login belongs to: an RRI login is a DENIC handle, which starts with its RegAccId
        (`DENIC-1000022-RRI` → `DENIC-1000022`)."""
        return "-".join(self.username.split("-")[:2]).upper()

    def verify_credentials(self, user, password) -> bool:
        return self.username == user and self.password == password

    def _log_in(self):
        login = RegistryRequest(login=LoginType(user=self.username, password=self.password))
        reply = str_to_rri(self._exchange(rri_to_str(login), loggable=False))
        if reply.transaction.result != ResultType.SUCCESS:
            codes = ", ".join(str(m.code) for m in reply.transaction.message)
            raise RriLoginError(f"RRI login refused: {codes}")

    def _log_out(self):
        if self._connected:
            self._exchange(rri_to_str(RegistryRequest(logout=LogoutType.VALUE)))

    def send(self, request: RegistryRequest, loggable=True) -> RegistryResponse:
        """Sends one request on the session and answers its parsed reply. `loggable` is False for a request that holds
        a secret (a CHPROV holds the AuthInfo in plaintext), which is then not printed."""
        return str_to_rri(self._round_trip(rri_to_str(request), loggable))
