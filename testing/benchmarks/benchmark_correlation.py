import time
from itertools import chain
from pprint import pprint

from benchmarks.generator import generate_correlated_by_ip_mac
from static_correlator.engine import StaticCorrelatorEngine


def correlate(devices):
    res = list(StaticCorrelatorEngine().correlate(devices))
    return res


def test_benchmark():
    generate = time.time()
    devices = [generate_correlated_by_ip_mac(x) for x in chain(range(0, 1000), range(0, 1000))]

    print(f'Generate in {time.time() - generate} {len(devices)} devices')

    corr = time.time()
    res = correlate(devices)
    print(f'Correlated in {time.time() - corr}, got {len(res)} correlation results')


if __name__ == '__main__':
    test_benchmark()
