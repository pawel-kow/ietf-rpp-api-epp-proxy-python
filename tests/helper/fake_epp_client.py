class FakeEppClient:
    """Stands in for EPPClient. Answers every command with the given EPP reply."""

    def __init__(self, username, password, reachable=True, reply=None):
        self.username = username
        self.password = password
        self.reachable = reachable
        self.reply = reply
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

    def send_and_get_response(self, message):
        self.sent.append(message)
        success, code, response = self.reply
        return success, code, response
