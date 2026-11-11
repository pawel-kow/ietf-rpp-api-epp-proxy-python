from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from core.session.session_pool import SessionPool
from tests.helper.fake_epp_client import FakeEppClient


class RecordingFactory:
    def __init__(self, reachable=True):
        self.reachable = reachable
        self.created = []

    def __call__(self, username, password):
        client = FakeEppClient(username, password, reachable=self.reachable)
        self.created.append(client)
        return client


def test_first_login_returns_a_connected_backend_from_the_factory():
    factory = RecordingFactory()

    result = SessionPool(factory).session("user", "pw")

    assert result == factory.created[0]
    assert factory.created[0].connected


def test_factory_receives_the_request_credentials():
    factory = RecordingFactory()

    SessionPool(factory).session("user", "pw")

    assert (factory.created[0].username, factory.created[0].password) == ("user", "pw")


def test_second_login_reuses_the_session():
    factory = RecordingFactory()
    sessions = SessionPool(factory)

    first = sessions.session("user", "pw")
    second = sessions.session("user", "pw")

    assert second is first
    assert len(factory.created) == 1


def test_each_user_gets_a_separate_session():
    factory = RecordingFactory()
    sessions = SessionPool(factory)

    first = sessions.session("user1", "pw")
    second = sessions.session("user2", "pw")

    assert second is not first


def test_failed_connect_is_rejected():
    assert SessionPool(RecordingFactory(reachable=False)).session("user", "pw") is None


def test_failed_connect_is_not_cached():
    factory = RecordingFactory(reachable=False)
    sessions = SessionPool(factory)

    sessions.session("user", "pw")
    factory.reachable = True

    assert sessions.session("user", "pw") == factory.created[1]


def test_wrong_password_on_a_cached_session_is_rejected():
    sessions = SessionPool(RecordingFactory())
    sessions.session("user", "pw")

    assert sessions.session("user", "wrong") is None


def test_sessions_are_not_shared_between_sessionss():
    factory = RecordingFactory()

    SessionPool(factory).session("user", "pw")
    SessionPool(factory).session("user", "pw")

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

    sessions = SessionPool(factory)

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: sessions.session("user", "pw"), range(2)))

    kept = results[0]
    assert results[1] is kept
    assert [c.disconnect_calls for c in created if c is not kept] == [1]
    assert kept.disconnect_calls == 0
