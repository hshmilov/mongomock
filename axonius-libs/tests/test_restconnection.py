"""
Notice! this requires rest_server.py to run (automatic as part of the CI).
"""
# pylint: disable=protected-access, redefined-outer-name
import threading
import time
import itertools

import urllib3

import pytest

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTAlreadyConnected
from axonius.thread_stopper import ThreadStopper

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class MockConnection(RESTConnection):
    def _connect(self):
        print(f'thread {threading.get_ident()}: connected to {self._domain}!')

    def get_device_list(self):
        yield from self._get(f'devices/5')


@pytest.fixture
def con():
    return MockConnection('https://localhost:33443', url_base_prefix='api')


def assert_connection_is_valid(con: MockConnection):
    assert list(con.get_device_list()) == [{'id': i} for i in range(5)]


def test_session_locked(con: MockConnection):
    assert con._is_connected is False
    assert con._session is None
    assert con._session_lock.locked() is False
    # Assert is_connected works
    with con:
        assert con._is_connected is True
        assert con._session is not None
        assert con._session_lock.locked() is True
        assert_connection_is_valid(con)

    assert con._is_connected is False
    assert con._session is None
    assert con._session_lock.locked() is False

    # Assert two connections can't be hold together
    con2 = con
    with con:
        assert_connection_is_valid(con)
        with pytest.raises(RESTAlreadyConnected):
            with con2:
                assert False, 'Should never get here'
        assert con._is_connected is True
        assert con._session is not None
        assert con._session_lock.locked() is True
        assert_connection_is_valid(con)

    assert con._is_connected is False
    assert con._session_lock.locked() is False
    assert con._session is None


def test_running_connection_doesnt_get_killed(con: MockConnection):
    """
    If a thread uses a RESTConnection (e.g. while in a cycle), a second thread that wants to use the connection
    shouldn't be able to stop it.
    :param con: MockConnection
    :return:
    """
    t1_event_t2_lock_acquired = threading.Event()
    t1_event_t2_can_exit = threading.Event()

    def acquire_mock_session(
            t2_event_t2_lock_acquired: threading.Event,
            t2_event_t2_can_exit: threading.Event
    ):
        con.__enter__()
        t2_event_t2_lock_acquired.set()
        assert t2_event_t2_can_exit.wait(timeout=5) is True, 'timeout!'

    t2 = threading.Thread(
        target=acquire_mock_session,
        args=(t1_event_t2_lock_acquired, t1_event_t2_can_exit),
        daemon=True
    )
    t2.start()
    # Wait until the thread actually acquires the lock
    t1_event_t2_lock_acquired.wait()
    # At this moment if we try to acquire con, we shouldn't be able to do this since the thread lives.
    con2 = con
    with pytest.raises(RESTAlreadyConnected):
        with con2:
            pass
    t1_event_t2_can_exit.set()
    t2.join()
    # The connection should still be valid.
    assert_connection_is_valid(con)


def test_connection_can_be_restored(con: MockConnection):
    """
    If a thread acquires a session lock and then gets brutally killed, a second thread should still be able to
    use the RESTConnection object since it will understand the original thread was killed.
    :param con: MockConnection
    :return:
    """
    t1_event = threading.Event()

    def acquire_mock_session_and_exit(t2_event: threading.Event):
        with con:
            t2_event.set()
            # we should time.sleep(1), if we time.sleep(10) in the first place the exception will run only after
            # the command.
            for i in range(30):
                time.sleep(1)
            assert False, 'should have never gotten here'

    t2 = threading.Thread(target=acquire_mock_session_and_exit, args=(t1_event, ), daemon=False)
    t2.start()
    assert t1_event.wait(timeout=30) is True, 'should have never gotten here'

    ThreadStopper.async_raise([t2.ident])

    # At this moment the lock should be acquired but the thread should be dead.
    t2.join(timeout=5)
    assert t2.is_alive() is False
    assert con._is_connected is False
    assert con._session_lock.locked() is False
    assert con._session is None

    # Lets see if we can use it using this thread.
    with con:
        assert_connection_is_valid(con)


def test_async_proxy_behavior():
    proxies = ['https://localhost', 'http://localhost', 'localhost']
    args = ['https_proxy', 'http_proxy']
    for arg, value in itertools.product(args, proxies):
        connection = MockConnection('https://localhost:33443', **{arg: value})
        aio_req = connection.create_async_dict({'name': 'test'}, 'get')
        assert aio_req['proxy'] == 'http://localhost'
