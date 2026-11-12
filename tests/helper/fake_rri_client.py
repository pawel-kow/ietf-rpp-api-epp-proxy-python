from registry_adapter.rri.gateways.rri_backend import RriBackend
from registry_adapter.rri.session.rri_client import RriClient
from registry_adapter.rri.xml.codec import rri_to_str, str_to_rri


class FakeRriClient(RriClient):
    """Stands in for the RRI session: answers each request with the next of `replies` (RRI XML), and keeps the XML it
    was sent in `sent`. An Exception entry is raised."""

    def __init__(self, username="DENIC-1000022-RRI", password="pw", replies=None, reachable=True):
        super().__init__(transport=None, username=username, password=password)
        self.replies = list(replies or [])
        self.reachable = reachable
        self.sent: list[str] = []

    def connect(self):
        self._connected = self.reachable

    def disconnect(self, send_logout=True):
        self._connected = False

    def send(self, request):
        self.sent.append(rri_to_str(request))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return str_to_rri(reply)


def rri_backends(client_factory, lgr=None):
    """A factory of backends over the RRI clients `client_factory` makes."""
    return lambda username, password: RriBackend(client_factory(username, password), lgr)


GLOBAL = 'xmlns="http://registry.denic.de/global/5.0" xmlns:tr="http://registry.denic.de/transaction/5.0"'

TEST_INFO = ('<tr:message level="info" code="13000000011"><tr:text>Request was processed in test environment - not '
             'valid in real world</tr:text><tr:argument>testing platform</tr:argument></tr:message>')


def reply(result="success", data="", messages="", stid="stid-1", ctid=None):
    """An RRI reply as MTEST sends it, with its test environment info."""
    ctid_xml = f"<tr:ctid>{ctid}</tr:ctid>" if ctid else ""
    data_xml = f"<tr:data>{data}</tr:data>" if data else ""
    return (f'<?xml version="1.0" encoding="UTF-8"?><registry-response {GLOBAL}><tr:transaction>'
            f'<tr:stid>{stid}</tr:stid>{ctid_xml}<tr:result>{result}</tr:result>{messages}{TEST_INFO}{data_xml}'
            f'</tr:transaction></registry-response>')


def error(code, text, argument=""):
    return reply("failed", messages=(f'<tr:message level="error" code="{code}"><tr:text>{text}</tr:text>'
                                     f'<tr:argument>{argument}</tr:argument></tr:message>'))
