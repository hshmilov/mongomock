"""
If the AXONIUS_TRACE environment variable exists, runs a thread that traces malloc and shows where memory is used.
Example:
    ./axonius.sh service heavy_lifting up --restart --prod --env AXONIUS_TRACE=1
"""
import os
import time
import tracemalloc
import threading
import logging


logger = logging.getLogger(f'axonius.{__name__}')
REPORTING_TIME_IN_MINUTES = 60 * 30


def log_message(message):
    formatted_message = f'Memory Tracer (PID {os.getpid()}): {message}'
    logger.info(formatted_message)


def trace_memory():
    log_message(f'Memory Tracer: Initialized memory tracing')
    last_memory_snapshot = tracemalloc.take_snapshot()
    while True:
        time.sleep(REPORTING_TIME_IN_MINUTES)
        try:
            now_memory_snapshot = tracemalloc.take_snapshot()
            diff = '\r\n'.join([str(i) for i in now_memory_snapshot.compare_to(last_memory_snapshot, 'lineno')[:20]])
            log_message(f'Memory Tracer: diff for last {REPORTING_TIME_IN_MINUTES} minutes: {diff}')
            last_memory_snapshot = now_memory_snapshot
        except Exception:
            log_message(f'Memory Tracer: Exception in trace_memory')


def run_memory_tracing():
    if os.environ.get('AXONIUS_TRACE'):
        tracemalloc.start()
        threading.Thread(target=trace_memory).start()
