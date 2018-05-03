import time
from itertools import chain
from pprint import pprint

from benchmarks.generator import generate_correlated_by_ip_mac, generate_correlated_serial, \
    generate_correlated_hostname_ip
from static_correlator.engine import StaticCorrelatorEngine

pairs = 200000


def correlate(devices):
    res = list(StaticCorrelatorEngine().correlate(devices))
    return res


def test_benchmark(msg, generate_func):
    generate = time.time()
    devices = [generate_func(x) for x in chain(range(0, pairs), range(0, pairs))]

    print(f'{msg} generate in {time.time() - generate} {len(devices)} devices')

    corr = time.time()
    res = correlate(devices)
    print(f'{msg} correlated in {time.time() - corr}, got {len(res)} correlation results')


if __name__ == '__main__':
    test_benchmark("MAC:", generate_correlated_by_ip_mac)
    test_benchmark("SERIAL:", generate_correlated_serial)
    test_benchmark("HOSTNAME_IP:", generate_correlated_hostname_ip)
