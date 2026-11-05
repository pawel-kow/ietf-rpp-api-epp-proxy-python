from eppclient.eppclient import SEC_DNS_EXTENSION


class FakeEppClient:
    """Stands in for EPPClient. Answers every command with the given EPP reply.

    `replies` answers commands in order instead. An Exception entry is raised.
    `extensions` is what the server offers in its greeting.
    """

    def __init__(self, username, password, reachable=True, reply=None, replies=None, extensions=(SEC_DNS_EXTENSION,)):
        self.username = username
        self.password = password
        self.reachable = reachable
        self.reply = reply
        self.replies = list(replies or [])
        self.extensions = extensions
        self.connected = False
        self.disconnect_calls = 0
        self.sent = []

    def connect(self):
        self.connected = self.reachable

    def disconnect(self):
        self.disconnect_calls += 1
        self.connected = False

    def verify_credentials(self, user, password):
        return self.username == user and self.password == password

    def supports_extension(self, uri):
        return uri in self.extensions

    def send_and_get_response(self, message):
        self.sent.append(message)
        reply = self.replies.pop(0) if self.replies else self.reply
        if isinstance(reply, Exception):
            raise reply
        success, code, response = reply
        return success, code, response
