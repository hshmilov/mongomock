import time

import pytest

from axonius.utils.retrying import retry_generator, RetryMaxTriesReached


@retry_generator()
def never_succeed():
    yield None
    raise ValueError('can never succeed')


@retry_generator(wait_fixed=2000)
def succeed_only_on_third_try(num):
    """
    Tries to yield numbers from 0 to num, but succeeds only on the third call of the function.
    This should test a get_devices() with timeout behaviour.
    :param num:
    :return:
    """

    try:
        succeed_only_on_third_try.try_num += 1
    except AttributeError:
        succeed_only_on_third_try.try_num = 1

    for i in range(num):
        yield i
        if succeed_only_on_third_try.try_num != 3:
            raise AssertionError('This is not the third try')


@retry_generator()
def succeed_on_first_try(num):
    for i in range(num):
        yield i


def test_retry_generator_succeeds_on_third_try():
    start_time = time.time()
    list_to_check = list(succeed_only_on_third_try(5))
    end_time = time.time()
    assert 4 < end_time - start_time < 6
    assert list_to_check == [0, 0, 0, 1, 2, 3, 4]


def test_retry_generator_succeeds_on_first_try():
    start_time = time.time()
    list_to_check = list(succeed_on_first_try(5))
    end_time = time.time()
    assert end_time - start_time < 1
    assert list_to_check == [0, 1, 2, 3, 4]


def test_retry_generator_gives_up():
    with pytest.raises(RetryMaxTriesReached):
        list(never_succeed())
