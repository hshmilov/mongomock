import time
from itertools import chain

from test_helpers.generator import generate_correlated_by_ip_mac, generate_correlated_serial, \
    generate_correlated_hostname_ip
from static_correlator.engine import StaticCorrelatorEngine

NUM_PAIRS = 100000


def correlate(devices):
    res = list(StaticCorrelatorEngine().correlate(devices))
    return res


def run_benchmark(msg, generate_func):
    generate = time.time()
    devices = [generate_func(x) for x in chain(range(1, NUM_PAIRS + 1), range(1, NUM_PAIRS + 1))]

    print(f'{msg} generate in {time.time() - generate} {len(devices)} devices')

    corr = time.time()
    res = correlate(devices)
    print(f'{msg} correlated in {time.time() - corr}, got {len(res)} correlation results')


# Correlation test case semi-automation
# (https://axonius.atlassian.net/wiki/spaces/AX/pages/655392769/Scaling+stress+tests , third case):
def test_correlation_benchmark():
    now = time.time()

    run_benchmark('MAC:', generate_correlated_by_ip_mac)
    run_benchmark('SERIAL:', generate_correlated_serial)
    run_benchmark('HOSTNAME_IP:', generate_correlated_hostname_ip)

    time_took = time.time() - now

    if time_took > 5 * 60:
        raise TimeoutError()
