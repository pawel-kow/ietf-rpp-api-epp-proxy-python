from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from controller.session_authenticator import SessionAuthenticator
from tests.helper.fake_epp_client import FakeEppClient


class RecordingFactory:
    def __init__(self, reachable=True):
        self.reachable = reachable
        self.created = []

    def __call__(self, username, password):
        client = FakeEppClient(username, password, reachable=self.reachable)
        self.created.append(client)
        return client


def test_first_login_returns_a_connected_client_from_the_factory():
    factory = RecordingFactory()

    result = SessionAuthenticator(factory).authenticate("user", "pw")

    assert result == {"backend": factory.created[0]}
    assert factory.created[0].connected


def test_factory_receives_the_request_credentials():
    factory = RecordingFactory()

    SessionAuthenticator(factory).authenticate("user", "pw")

    assert (factory.created[0].username, factory.created[0].password) == ("user", "pw")


def test_second_login_reuses_the_session():
    factory = RecordingFactory()
    authenticator = SessionAuthenticator(factory)

    first = authenticator.authenticate("user", "pw")
    second = authenticator.authenticate("user", "pw")

    assert second["backend"] is first["backend"]
    assert len(factory.created) == 1


def test_each_user_gets_a_separate_session():
    factory = RecordingFactory()
    authenticator = SessionAuthenticator(factory)

    first = authenticator.authenticate("user1", "pw")
    second = authenticator.authenticate("user2", "pw")

    assert second["backend"] is not first["backend"]


def test_failed_connect_is_rejected():
    assert SessionAuthenticator(RecordingFactory(reachable=False)).authenticate("user", "pw") is None


def test_failed_connect_is_not_cached():
    factory = RecordingFactory(reachable=False)
    authenticator = SessionAuthenticator(factory)

    authenticator.authenticate("user", "pw")
    factory.reachable = True

    assert authenticator.authenticate("user", "pw") == {"backend": factory.created[1]}


def test_wrong_password_on_a_cached_session_is_rejected():
    authenticator = SessionAuthenticator(RecordingFactory())
    authenticator.authenticate("user", "pw")

    assert authenticator.authenticate("user", "wrong") is None


def test_sessions_are_not_shared_between_authenticators():
    factory = RecordingFactory()

    SessionAuthenticator(factory).authenticate("user", "pw")
    SessionAuthenticator(factory).authenticate("user", "pw")

    assert len(factory.created) == 2


def test_concurrent_first_logins_keep_one_session_and_disconnect_the_rest():
    barrier = Barrier(2)

    class RacingClient(FakeEppClient):
        def connect(self):
            super().connect()
            barrier.wait(timeout=5)

    created = []

    def factory(username, password):
        client = RacingClient(username, password)
        created.append(client)
        return client

    authenticator = SessionAuthenticator(factory)

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: authenticator.authenticate("user", "pw"), range(2)))

    kept = results[0]["backend"]
    assert results[1]["backend"] is kept
    assert [c.disconnect_calls for c in created if c is not kept] == [1]
    assert kept.disconnect_calls == 0
