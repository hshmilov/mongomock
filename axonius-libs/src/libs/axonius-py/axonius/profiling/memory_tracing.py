"""
If the AXONIUS_TRACE environment variable exists, runs a thread that traces malloc and shows where memory is used.
Example:
    ./axonius.sh service heavy_lifting up --restart --prod --env AXONIUS_TRACE=1
"""
import linecache
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


def get_pretty_top(snapshot, key_type='lineno', limit=10):
    snapshot = snapshot.filter_traces((
        tracemalloc.Filter(False, '<frozen importlib._bootstrap>'),
        tracemalloc.Filter(False, '<unknown>'),
    ))
    top_stats = snapshot.statistics(key_type)

    msg = [f'Top {limit} lines:']
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        # replace "/path/to/module/file.py" with "module/file.py"
        filename = os.sep.join(frame.filename.split(os.sep)[-2:])
        msg.append(f'#{index}: {filename}:{frame.lineno}: {stat.size / 1024} KiB')
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            msg.append(f'    {line}')

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        msg.append(f'{len(other)} other: {size / 1024} KiB')
    total = sum(stat.size for stat in top_stats)
    msg.append(f'Total allocated size: {total / 1024} KiB')

    return '\r\n'.join(msg)


def trace_memory():
    log_message(f'Memory Tracer: Initialized memory tracing')
    last_memory_snapshot = tracemalloc.take_snapshot()
    while True:
        time.sleep(REPORTING_TIME_IN_MINUTES)
        try:
            now_memory_snapshot = tracemalloc.take_snapshot()
            diff = '\r\n'.join([str(i) for i in now_memory_snapshot.compare_to(last_memory_snapshot, 'lineno')[:20]])
            log_message(f'diff for last {REPORTING_TIME_IN_MINUTES} minutes: {diff}')
            last_memory_snapshot = now_memory_snapshot

            # pick the biggest memory block
            top_stats = now_memory_snapshot.statistics('traceback')
            stat = top_stats[0]
            msg = [f'{stat.count} memory blocks: {stat.size / 1024} KiB']
            msg.extend([str(i) for i in stat.traceback.format()])
            formatted_message = '\r\n'.join(msg)
            log_message(get_pretty_top(now_memory_snapshot))
            log_message(f'Top line traceback: {formatted_message}')
        except Exception:
            log_message(f'Exception in trace_memory')


def run_memory_tracing():
    if os.environ.get('AXONIUS_TRACE'):
        tracemalloc.start(25)   # store 25 frames
        threading.Thread(target=trace_memory).start()
