#!/usr/bin/env python

import os

from redseal_adapter.client import RedSealClient
from testing.test_credentials.test_redseal_credentials import client_details
from pprint import pprint

import logging
import warnings
import time

warnings.filterwarnings('ignore', 'Unverified HTTPS request')


def test_devices():
    client = RedSealClient(**client_details)
    client.check_connection()
    result = list(client.get_devices())
    assert len(result) > 0
    return result


def get_device(devices):
    for device in devices:
        d = list(device.values())[0]
        if d.get('TreeId') == '402894aa63efb60a01640e786855045e':
            return device


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    start = time.time()
    devices = list(test_devices())
    device = get_device(devices)
    pprint(devices)
    pprint(device)
    print(time.time() - start)
