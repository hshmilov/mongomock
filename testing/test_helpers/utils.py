import time


def try_until_not_thrown(times, sleep_period, runnable, *args, **kwargs):
    success = False
    for x in range(1, times):
        try:
            runnable(*args, **kwargs)
            success = True
            return
        except:
            time.sleep(sleep_period)
    assert success
