class EppSessionAuthenticator:
    """
    Authenticates requests against EPP sessions, keeping one session per user.
    """

    def __init__(self, client_factory):
        """
        Args:
            client_factory: Called with (username, password), returns a new EPP client.
        """
        self._client_factory = client_factory
        self._sessions = {}

    def authenticate(self, username, password):
        """
        Returns the token info holding the user's EPP client, or None if rejected.
        """
        client = self._sessions.get(username)
        if client is None:
            new_client = self._client_factory(username, password)
            new_client.connect()
            if not new_client.connected:
                return None
            # Concurrent first requests may each log in. setdefault is atomic, so exactly
            # one session is kept for the user and all requests share it.
            client = self._sessions.setdefault(username, new_client)
            if client is not new_client:
                new_client.disconnect()

        if not client.verify_credentials(username, password):
            return None

        return {
            "epp_client": client
        }
