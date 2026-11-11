from connexion.security import BasicSecurityHandler

from rpp.http.context import TOKEN_BACKEND


class SessionSecurityHandler(BasicSecurityHandler):
    """
    HTTP Basic handler that logs a user in through the session pool it is given, instead of a function resolved by
    name. The token info holds the user's backend.
    """

    def __init__(self, sessions):
        """
        Args:
            sessions: The `SessionPool`.
        """
        self._sessions = sessions

    def _resolve_func(self, security_scheme):
        return self._token_info

    def _token_info(self, username, password):
        backend = self._sessions.session(username, password)
        return None if backend is None else {TOKEN_BACKEND: backend}
