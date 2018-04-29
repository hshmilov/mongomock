#!/usr/bin/env python3
"""
This script starts the system [in production (--prod)]
                              [with all (--all) services & adapters] or
                              [with specific services & adapters (--services & --adapters)]
"""
import argparse
import subprocess
import sys

from utils import AutoOutputFlush, get_service


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prod', action='store_true', default=False, help='Prod Mode')
    parser.add_argument('--all', action='store_true', default=False, help='All adapters and services')
    parser.add_argument('--services', metavar='N', type=str, nargs='*', help='Services to activate', default=[])
    parser.add_argument('--adapters', metavar='N', type=str, nargs='*', help='Adapters to activate', default=[])

    try:
        args = parser.parse_args()
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    mode = 'prod' if args.prod else ''
    axonius_system = get_service()
    axonius_system.take_process_ownership()

    if args.all:
        assert len(args.services) == 0 and len(args.adapters) == 0
        args.services = [name for name, variable in axonius_system.get_all_plugins() if variable().get_image_exists()]
        args.adapters = [name for name, variable in axonius_system.get_all_adapters() if variable().get_image_exists()]

    print(f'Starting system and {args.adapters + args.services}')

    if 'axonius' not in subprocess.check_output(['docker', 'network', 'ls',
                                                 '--filter', 'name=axonius']).decode('utf-8'):
        subprocess.check_call(['docker', 'network', 'create', 'axonius'], stdout=subprocess.PIPE)
    axonius_system.start_and_wait(mode, True, show_print=False)
    axonius_system.start_plugins(args.adapters, args.services, mode, True, show_print=False)


if __name__ == '__main__':
    with AutoOutputFlush():
        main()
