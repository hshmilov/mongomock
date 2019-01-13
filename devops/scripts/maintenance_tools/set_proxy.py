#!/usr/bin/env python3

import argparse
import sys
import pprint

from axonius.consts.core_consts import CORE_CONFIG_NAME
from axonius.consts.plugin_consts import PROXY_SETTINGS
from testing.services.plugins.core_service import CoreService


def main(args):
    if args.read:
        print('Reading:')
        print(CoreService().get_configurable_config(CORE_CONFIG_NAME)[PROXY_SETTINGS])
    else:
        settings = {'enabled': args.enabled,
                    'proxy_addr': args.addr,
                    'proxy_password': args.password,
                    'proxy_port': args.port,
                    'proxy_user': args.user}
        print(f'Setting proxy settings {settings}')
        pprint.pprint(settings)
        set_proxy(settings)


def set_proxy(settings):
    cs = CoreService()
    cs.set_configurable_config(CORE_CONFIG_NAME, PROXY_SETTINGS, settings)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--enabled', default=False, type=bool)
    parser.add_argument('--addr', default='', type=str)
    parser.add_argument('--port', default=8080, type=int)
    parser.add_argument('--password', default='', type=str)
    parser.add_argument('--user', default='', type=str)
    parser.add_argument('-read', action='store_true')

    try:
        args = parser.parse_args()
    except Exception:
        print(parser.usage())
        sys.exit(1)
    return args


if __name__ == '__main__':
    args = parse_args()

    main(args)
