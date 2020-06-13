import logging
import sys
import time

import segfault

from axonius.multiprocess.multiprocess import concurrent_multiprocess_yield


def yield_numbers_with_sleep(numbers: int, sleep: int, freeze_in_number):
    for i in range(numbers):
        yield i
        time.sleep(sleep)
        if i == freeze_in_number:
            print(f'Segfaulting...')
            time.sleep(2)
            segfault.segfault()


def test_concurrent_multiprocess_yield_normal():
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    def do_the_yield():
        _ = (yield from concurrent_multiprocess_yield(
            [
                (
                    yield_numbers_with_sleep,
                    (
                        4,
                        1,
                        None
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


def test_abrupt_shutdown():
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    def do_the_yield():
        _ = (yield from concurrent_multiprocess_yield(
            [
                (
                    yield_numbers_with_sleep,
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
