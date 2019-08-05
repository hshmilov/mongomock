# mocking flask.request and jsonify
from threading import Lock
from retrying import retry
import flask
import mongomock


class MockRequest():
    @staticmethod
    def get_json(*args, **kwargs):
        return {"s": "d"}

    headers = {"x-api-key": "asd"}


flask.request = MockRequest
flask.jsonify = lambda x: x

import axonius.plugin_base


def mock_empty_decorator(*args, **kwargs):
    def wrap(func):
        def actual_wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return actual_wrapper

    return wrap


# mock @add_rule

axonius.plugin_base.add_rule = mock_empty_decorator
from axonius.mixins.triggerable import Triggerable
import logging

import sys

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(' [Triggerable] %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class WaitableTriggerableImplementedMock(Triggerable):
    """
    Just a parent class for the rest of the classes.
    """

    def __init__(self, *args, **kwargs):
        """
        init.
        """
        self.db = mongomock.MongoClient().db
        self.logger = logger
        self.api_key = 'asd'
        self.counter = 0
        super().__init__(*args, **kwargs)

    def _get_collection(self, collection_name):
        """
        Mock to _get_collection
        :param collection_name: the name of the collection
        :return: the collection mock
        """

        return self.db[collection_name]

    def get_caller_plugin_name(self):
        return 'plugin', 'name'


class SimpleWaitableTriggerableImplementedMock(WaitableTriggerableImplementedMock):
    def __init__(self, wait_for, *args, **kwargs):
        self.__wait_for = wait_for
        super().__init__(*args, **kwargs)

    def _triggered(self, job_name, post_json, *args):
        self.counter += 1
        return job_name


@retry(wait_fixed=20,
       stop_max_delay=2000)
def verify_state(triggerable, state, job_name):
    res = triggerable._get_state(job_name)
    assert state['state'] == res['state']
    assert state['last_error'] in res['last_error']
    return True


@retry(wait_fixed=20,
       stop_max_delay=2000)
def retry_assert_equal(a, b):
    assert a == b, f"{a} != {b}"


def runall():
    test_trigger_activated()
    test_double_trigger()
    test_double_trigger_with_failure()


def test_trigger_activated():
    lock = Lock()
    job_name = 'ds'
    x = SimpleWaitableTriggerableImplementedMock({job_name: lock})
    x._trigger(job_name)
    assert x._get_state(job_name) == {
        "state": "Scheduled",
        "last_error": "ds"
    }
    retry_assert_equal(x.counter, 1)


def test_double_trigger():
    lock = Lock()
    job_name = 'ds'
    x = SimpleWaitableTriggerableImplementedMock({job_name: lock})
    x._trigger(job_name)
    assert x._get_state(job_name) == {
        "state": "Scheduled",
        "last_error": "ds"
    }
    retry_assert_equal(x.counter, 1)
    x._trigger(job_name)

    assert verify_state(x, {
        "state": "Scheduled",
        "last_error": "ds"
    }, job_name)
    retry_assert_equal(x.counter, 2)


class FailingWaitableTriggerableImplementedMock(WaitableTriggerableImplementedMock):
    def __init__(self, wait_for, fail_array, *args, **kwargs):
        self.__wait_for = wait_for
        self.__fail_array = fail_array
        super().__init__(*args, **kwargs)

    def _triggered(self, job_name, post_json, *args):
        self.counter += 1
        if self.__fail_array[self.counter - 1]:
            raise Exception(f"Fail {self.counter}")
        return job_name


def test_double_trigger_with_failure():
    lock = Lock()
    job_name = 'ds'
    caught_exception = False
    x = FailingWaitableTriggerableImplementedMock({job_name: lock}, [False, True])
    try:
        x._trigger(job_name)
    except Exception:
        logger.exception(f"Exception: {e}")
        caught_exception = True

    assert not caught_exception
    caught_exception = False

    assert x._get_state(job_name) == {
        "state": "Scheduled",
        "last_error": "ds"
    }
    retry_assert_equal(x.counter, 1)
    try:
        x._trigger(job_name)
    except Exception as e:
        logger.exception(f"Exception: {e}")
        caught_exception = True

    assert not caught_exception

    assert verify_state(x, {
        "state": "Scheduled",
        "last_error": "Fail 2"
    }, job_name)
    retry_assert_equal(x.counter, 2)
