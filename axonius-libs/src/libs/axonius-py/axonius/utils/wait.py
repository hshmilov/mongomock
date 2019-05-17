import time


def wait_until(func,
               check_return_value=True,
               total_timeout=60,
               interval=0.5,
               tolerated_exceptions_list=None,
               error_message='',
               **kwargs):
    """
    This waits until the conditions according to the arguments are met.
    :param func: The fuction to rerun until the conditions are met.
    :param check_return_value: whether should check if the func returns True
    :type check_return_value: bool
    :param total_timeout: The total time this method should wait for the desired result.
    :type total_timeout: float
    :param interval: The interval in which we should wait between each retry (rerun of func).
    :type interval: float
    :param tolerated_exceptions_list: A list of Exceptions that should be tolerated if they are raised by func.
    :type tolerated_exceptions_list: list
    :param error_message: The message that should be written in the TimeoutError when raised (For logging purposes).
    :type error_message: str
    :param exception_expected: If you want to wait for a specific Exception to be raised by func.
    :return: The value returned by func.
    """
    start_time = time.time()
    while time.time() - start_time < total_timeout:

        try:
            return_value = func(**kwargs)
            if not check_return_value or (check_return_value and return_value):
                return return_value
        except Exception as e:
            if tolerated_exceptions_list and any(isinstance(e, x) for x in tolerated_exceptions_list):
                pass
            else:
                raise

        time.sleep(interval)

    raise TimeoutError(error_message)


def expect_specific_exception_to_be_raised(func, expected_exception):
    """
    This is a util to help users of wait for a specific exception to be raised by the func()
    :param func: The function to run.
    :param expected_exception: The Exception class to be expected to be raised.
    :return: True if the correct exception was raised.
    """
    try:
        func()
        return False
    except expected_exception:
        return True
