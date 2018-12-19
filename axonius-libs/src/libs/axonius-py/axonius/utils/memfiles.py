import os
from contextlib import contextmanager

import memfd


@contextmanager
def temp_memfd(name, data: bytes):
    with memfd.open(name) as mfd:
        mfd.write(data)
        yield f'/proc/{os.getpid()}/fd/{mfd.fileno()}'
