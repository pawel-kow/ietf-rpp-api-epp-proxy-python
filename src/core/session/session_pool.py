class SessionPool:
    """
    Keeps one registry session per user, so the requests of a user share it.
    """

    def __init__(self, backend_factory):
        """
        Args:
            backend_factory: Called with (username, password), returns a new `RegistryBackend`, the user's session.
        """
        self._backend_factory = backend_factory
        self._sessions = {}

    def session(self, username, password):
        """
        Returns the user's backend, logged in, or None if rejected.
        """
        backend = self._sessions.get(username)
        if backend is None:
            new_backend = self._backend_factory(username, password)
            new_backend.connect()
            if not new_backend.connected:
                return None
            # Concurrent first requests may each log in. setdefault is atomic, so exactly
            # one session is kept for the user and all requests share it.
            backend = self._sessions.setdefault(username, new_backend)
            if backend is not new_backend:
                new_backend.disconnect()

        if not backend.verify_credentials(username, password):
            return None

        return backend

    def close(self):
        """Logs every session out, so the registry does not count it until its idle timeout. A later request of a
        user logs in again."""
        sessions, self._sessions = self._sessions, {}
        for backend in sessions.values():
            backend.disconnect()
