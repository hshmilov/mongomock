# mocking flask.request and jsonify
from threading import Lock

import flask
from retrying import retry


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


class SimpleWaitableTriggerableImplementedMock(Triggerable):
    def __init__(self, wait_for, *args, **kwargs):
        self.logger = logger
        self.api_key = 'asd'
        self.__wait_for = wait_for
        self.counter = 0
        super().__init__(*args, **kwargs)

    def _triggered(self, job_name, post_json, *args):
        self.counter += 1
        return job_name


@retry(wait_fixed=20,
       stop_max_delay=2000)
def verify_state(triggerable, state, job_name):
    res = triggerable.get_trigger_activatable_state(job_name)
    assert res == state, f"Not equal {res} and {state}"
    return True


@retry(wait_fixed=20,
       stop_max_delay=2000)
def retry_assert_equal(a, b):
    assert a == b, f"{a} != {b}"


def runall():
    test_trigger_disabled()
    test_trigger_activated()
    test_double_trigger()
    test_double_trigger_with_failure()


def test_trigger_disabled():
    lock = Lock()
    job_name = 'ds'
    x = SimpleWaitableTriggerableImplementedMock({job_name: lock})
    response = x.trigger(job_name)
    assert response == ''
    retry_assert_equal(x.counter, 0)

    assert verify_state(x, {
        "state": "Disabled",
        "last_error": ""
    }, job_name)
    retry_assert_equal(x.counter, 0)


def test_trigger_activated():
    lock = Lock()
    job_name = 'ds'
    x = SimpleWaitableTriggerableImplementedMock({job_name: lock})
    response = x._activate(job_name)
    assert response == ''
    x.trigger(job_name)
    assert x.get_trigger_activatable_state(job_name) == {
        "state": "Scheduled",
        "last_error": ""
    }
    retry_assert_equal(x.counter, 1)


def test_double_trigger():
    lock = Lock()
    job_name = 'ds'
    x = SimpleWaitableTriggerableImplementedMock({job_name: lock})
    x._activate(job_name)
    x.trigger(job_name)
    assert x.get_trigger_activatable_state(job_name) == {
        "state": "Scheduled",
        "last_error": ""
    }
    retry_assert_equal(x.counter, 1)
    x.trigger(job_name)

    assert verify_state(x, {
        "state": "Scheduled",
        "last_error": ""
    }, job_name)
    retry_assert_equal(x.counter, 2)


class FailingWaitableTriggerableImplementedMock(Triggerable):
    def __init__(self, wait_for, fail_array, *args, **kwargs):
        self.logger = logger
        self.api_key = 'asd'
        self.__wait_for = wait_for
        self.__fail_array = fail_array
        self.counter = 0
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
    x._activate(job_name)
    try:
        x.trigger(job_name)
    except Exception:
        caught_exception = True

    assert not caught_exception
    caught_exception = False

    assert x.get_trigger_activatable_state(job_name) == {
        "state": "Scheduled",
        "last_error": ""
    }
    retry_assert_equal(x.counter, 1)
    try:
        x.trigger(job_name)
    except Exception:
        caught_exception = True

    assert caught_exception

    assert verify_state(x, {
        "state": "Scheduled",
        "last_error": "Exception('Fail 2',)"
    }, job_name)
    retry_assert_equal(x.counter, 2)
