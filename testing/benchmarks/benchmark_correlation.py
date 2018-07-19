import time
from itertools import chain

from benchmarks.generator import generate_correlated_by_ip_mac, generate_correlated_serial, \
    generate_correlated_hostname_ip
from static_correlator.engine import StaticCorrelatorEngine

pairs = 100000


def correlate(devices):
    res = list(StaticCorrelatorEngine().correlate(devices))
    return res


def test_benchmark(msg, generate_func):
    generate = time.time()
    devices = [generate_func(x) for x in chain(range(1, pairs + 1), range(1, pairs + 1))]

    print(f'{msg} generate in {time.time() - generate} {len(devices)} devices')

    corr = time.time()
    res = correlate(devices)
    print(f'{msg} correlated in {time.time() - corr}, got {len(res)} correlation results')


# Correlation test case semi-automation
# (https://axonius.atlassian.net/wiki/spaces/AX/pages/655392769/Scaling+stress+tests , third case):

if __name__ == '__main__':

    now = time.time()

    test_benchmark("MAC:", generate_correlated_by_ip_mac)
    test_benchmark("SERIAL:", generate_correlated_serial)
    test_benchmark("HOSTNAME_IP:", generate_correlated_hostname_ip)

    time_took = time.time() - now

    if time_took > 5 * 60:
        print('FAILED')
    else:
        print('PASSED')
