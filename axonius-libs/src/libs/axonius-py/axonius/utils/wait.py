import time


def wait_until(func,
               check_return_value=True,
               total_timeout=60,
               interval=0.5,
               exc_list=None,
               error_message='',
               **kwargs):
    start_time = time.time()
    while time.time() - start_time < total_timeout:

        try:
            return_value = func(**kwargs)
            if not check_return_value or (check_return_value and return_value):
                return return_value

        except Exception as e:
            if exc_list and any(isinstance(e, x) for x in exc_list):
                pass
            else:
                raise

        time.sleep(interval)

    raise TimeoutError(error_message)
