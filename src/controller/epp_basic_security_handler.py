from connexion.security import BasicSecurityHandler


class EppBasicSecurityHandler(BasicSecurityHandler):
    """
    HTTP Basic handler that uses the given function instead of one resolved by name.
    """

    def __init__(self, authenticate):
        """
        Args:
            authenticate: Called with (username, password), returns the token info or None.
        """
        self._authenticate = authenticate

    def _resolve_func(self, security_scheme):
        return self._authenticate
