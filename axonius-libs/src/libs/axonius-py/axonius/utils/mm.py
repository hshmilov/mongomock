import gc
import time

from axonius.utils.threading import run_and_forget


def delayed_trigger_gc():
    # https://axonius.atlassian.net/browse/AX-2996
    # Sometimes it is crucial that the GC runs for the safe execution of the system.
    # The reason this is not called, for example, from triggerable itself, is because gc.collect
    # takes quite a while and takes the GIL, thus the whole app is waiting.
    # Therefore if this is called too much (i.e. every trigger) the plugin will constantly stutter.
    def _inner():
        time.sleep(3)
        gc.collect(2)
    run_and_forget(_inner)
