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
        with self.__wait_for[job_name]:
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
    test_trigger_basic()
    test_double_trigger()
    test_too_much_trigger()
    test_two_jobs_parallelization()
    test_double_trigger_with_failure()


def test_trigger_basic():
    lock = Lock()
    job_name = 'ds'
    x = SimpleWaitableTriggerableImplementedMock({job_name: lock})
    with lock:
        x.trigger(job_name)
        assert x.get_trigger_activatable_state(job_name) == {
            "state": "Triggered",
            "last_error": ""
        }
        retry_assert_equal(x.counter, 1)

    assert verify_state(x, {
        "state": "Idle",
        "last_error": ""
    }, job_name)
    retry_assert_equal(x.counter, 1)


def test_double_trigger():
    lock = Lock()
    job_name = 'ds'
    x = SimpleWaitableTriggerableImplementedMock({job_name: lock})
    with lock:
        x.trigger(job_name)
        assert x.get_trigger_activatable_state(job_name) == {
            "state": "Triggered",
            "last_error": ""
        }
        retry_assert_equal(x.counter, 1)
        x.trigger(job_name)

    assert verify_state(x, {
        "state": "Idle",
        "last_error": ""
    }, job_name)
    retry_assert_equal(x.counter, 2)


def test_too_much_trigger():
    # test that calling trigger more than 2 times in parallel will always result in 2 calls
    lock = Lock()
    job_name = 'ds'
    x = SimpleWaitableTriggerableImplementedMock({job_name: lock})
    with lock:
        x.trigger(job_name)
        assert x.get_trigger_activatable_state(job_name) == {
            "state": "Triggered",
            "last_error": ""
        }
        retry_assert_equal(x.counter, 1)
        x.trigger(job_name)
        x.trigger(job_name)
        x.trigger(job_name)

    assert verify_state(x, {
        "state": "Idle",
        "last_error": ""
    }, job_name)
    retry_assert_equal(x.counter, 2)


def test_two_jobs_parallelization():
    locks = Lock(), Lock()
    job_names = 'ds', 'ds2'
    x = SimpleWaitableTriggerableImplementedMock(dict(zip(job_names, locks)))

    locks[0].acquire()
    locks[1].acquire()

    x.trigger(job_names[0])
    retry_assert_equal(x.counter, 1)
    assert x.get_trigger_activatable_state(job_names[0]) == {
        "state": "Triggered",
        "last_error": ""
    }

    x.trigger(job_names[1])
    assert x.get_trigger_activatable_state(job_names[1]) == {
        "state": "Triggered",
        "last_error": ""
    }
    retry_assert_equal(x.counter, 2)

    locks[0].release()
    assert verify_state(x, {
        "state": "Idle",
        "last_error": ""
    }, job_names[0])
    retry_assert_equal(x.counter, 2)

    locks[1].release()
    assert verify_state(x, {
        "state": "Idle",
        "last_error": ""
    }, job_names[1])
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
        with self.__wait_for[job_name]:
            if self.__fail_array[self.counter - 1]:
                raise Exception(f"Fail {self.counter}")
            return job_name


def test_double_trigger_with_failure():
    lock = Lock()
    job_name = 'ds'
    x = FailingWaitableTriggerableImplementedMock({job_name: lock}, [False, True])
    with lock:
        x.trigger(job_name)
        assert x.get_trigger_activatable_state(job_name) == {
            "state": "Triggered",
            "last_error": ""
        }
        retry_assert_equal(x.counter, 1)
        x.trigger(job_name)

    assert verify_state(x, {
        "state": "Idle",
        "last_error": "Exception('Fail 2',)"
    }, job_name)
    retry_assert_equal(x.counter, 2)
