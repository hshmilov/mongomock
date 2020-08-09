import logging
import sys
import threading
import time

import func_timeout
import pytest
import segfault

from axonius.multiprocess.multiprocess import concurrent_multiprocess_yield
from axonius.thread_stopper import ThreadStopper

THREE_DAYS_SECS = 60 * 60 * 60 * 24 * 3


def yield_numbers_with_sleep_and_crash(numbers: int, sleep: int, freeze_in_number):
    for i in range(numbers):
        yield i
        time.sleep(sleep)
        if i == freeze_in_number:
            print(f'Segfaulting...')
            time.sleep(2)
            segfault.segfault()


def yield_numbers_with_sleep(numbers: int, sleep: int):
    for i in range(numbers):
        yield i
        time.sleep(sleep)

    return numbers


def yield_numbers_and_raise(numbers: int, raise_on: int, sleep_between_yield: int):
    for i in range(numbers):
        time.sleep(sleep_between_yield)
        yield i
        if i == raise_on:
            raise ValueError('Some Error')


def test_concurrent_multiprocess_yield_normal():
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    def do_the_yield():
        _ = (yield from concurrent_multiprocess_yield(
            [
                (
                    yield_numbers_with_sleep,
                    (
                        4,
                        1
                    ),
                    {}
                )
            ],
            1
        ))
    res = []
    for i in do_the_yield():
        res.append(i)
        print(i)

    assert res == [0, 1, 2, 3]

    print(f'Finished! Exiting..')


def test_yield_different_times_and_ret_value():
    # Tests two processes that have different times that are bigger then the interval we have for checking
    # for results. the times must be big
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    def do_the_yield():
        ret = (yield from concurrent_multiprocess_yield(
            [
                (
                    yield_numbers_with_sleep,
                    (
                        10,
                        1
                    ),
                    {}
                ),
                (
                    yield_numbers_with_sleep,
                    (
                        5,
                        5
                    ),
                    {}
                )
            ],
            4
        ))
        assert ret == [10, 5]
        return ret

    res = []
    for i in do_the_yield():
        res.append(i)
        print(i)

    assert sorted(res) == [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 6, 7, 8, 9]

    print(f'Finished! Exiting..')


def test_abrupt_shutdown():
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    def do_the_yield():
        _ = (yield from concurrent_multiprocess_yield(
            [
                (
                    yield_numbers_with_sleep_and_crash,
                    (
                        4,
                        1,
                        1
                    ),
                    {}
                )
            ],
            1
        ))
    for i in do_the_yield():
        print(i)

    print(f'Finished! Exiting..')
    # This point will get stuck forever if the process does not shut down correctly.


def test_func_timeout():
    # tests entity timeout
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    def do_the_yield():
        _ = (yield from concurrent_multiprocess_yield([(time.sleep, (THREE_DAYS_SECS, ), {})], 1))

    def call_do_the_yield():
        for i in do_the_yield():
            print(i)

    # This point will get stuck forever if the process does not shut down correctly.
    with pytest.raises(func_timeout.exceptions.FunctionTimedOut):
        func_timeout.func_timeout(timeout=2, func=call_do_the_yield, args=[])


def test_thread_stopper():
    # Tests stop cycle
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    def do_the_yield():
        _ = (yield from concurrent_multiprocess_yield([(time.sleep, (THREE_DAYS_SECS, ), {})], 1))

    def call_do_the_yield():
        for i in do_the_yield():
            print(i)

    # This point will get stuck forever if the process does not shut down correctly.
    yield_thread = threading.Thread(target=call_do_the_yield)
    yield_thread.start()
    time.sleep(2)
    ThreadStopper.async_raise([yield_thread.ident])


def test_regular_exception():
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    def do_the_yield():
        _ = (
            yield from concurrent_multiprocess_yield(
                [
                    (yield_numbers_and_raise, (3, 0, 1), {}),
                    (yield_numbers_and_raise, (3, -1, 1), {})
                ],
                3
            )
        )

    # This point will get stuck forever if the process does not shut down correctly.
    for i in do_the_yield():
        print(i)
    print('Done')


if __name__ == '__main__':
    test_regular_exception()
    sys.exit(0)
