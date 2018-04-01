#!/usr/bin/env python

import argparse
import os
import sys


try:
    import axonius
except (ModuleNotFoundError, ImportError):
    # if not in path...
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'plugins', 'axonius-libs',
                                                 'src', 'libs', 'axonius-py')))


try:
    from services.axonius_service import get_service
except (ModuleNotFoundError, ImportError):
    # if not in path...
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'testing')))
    from services.axonius_service import get_service


def main():
    parser = argparse.ArgumentParser(description='Axonius system startup', usage="""
{name} [-h] {system,adapter,service} [<args>]
       {name} system [-h] {up,down,build} [--all] [--prod] [--restart] [--rebuild] [--hard] [--pull-base-image] [--skip]
                                [--services [N [N ...]]] [--adapters [N [N ...]]] [--exclude [N [N ...]]]
       {name} {adapter,service} [-h] name {up,down,build} [--prod] [--restart] [--rebuild] [--hard]
       {name} ls
"""[1:].replace('{name}', os.path.basename(__file__)))
    parser.add_argument('target', choices=['system', 'adapter', 'service', 'ls'])

    try:
        args = parser.parse_args(sys.argv[1:2])
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    if args.target == 'system':
        system_entry_point(sys.argv[2:])
    elif args.target == 'ls':
        axonius_system = get_service()
        print('Core Services:')
        for service in axonius_system.axonius_services:
            print(f'    {service.container_name}')
        print('Services:')
        for name, _ in axonius_system.get_all_plugins():
            print(f'    {name}')
        print('Adapters:')
        for name, _ in axonius_system.get_all_adapters():
            print(f'    {name}')
    else:
        service_entry_point(args.target, sys.argv[2:])


def system_entry_point(args):
    parser = argparse.ArgumentParser(description='Axonius system startup', usage="""
{name} system [-h] {up,down,build} [--all] [--prod] [--restart] [--rebuild] [--hard] [--skip]
                                [--services [N [N ...]]] [--adapters [N [N ...]]] [--exclude [N [N ...]]]"""[1:].
                                     replace('{name}', os.path.basename(__file__)))
    parser.add_argument('mode', choices=['up', 'down', 'build'])
    parser.add_argument('--all', type=str2bool, nargs='?', const=True, default=False, help='All adapters and services')
    parser.add_argument('--prod', type=str2bool, nargs='?', const=True, default=False, help='Prod Mode')
    parser.add_argument('--restart', type=str2bool, nargs='?', const=True, default=False,
                        help='Restart container')
    parser.add_argument('--rebuild', type=str2bool, nargs='?', const=True, default=False, help='Rebuild Image')
    parser.add_argument('--hard', type=str2bool, nargs='?', const=True, default=False,
                        help='Rebuild Image after rebuilding axonius-libs')
    parser.add_argument('--pull-base-image', action='store_true', default=False, help='Pull base image before rebuild')
    parser.add_argument('--skip', type=str2bool, nargs='?', const=True, default=False,
                        help='Skip already up containers')
    parser.add_argument('--services', metavar='N', type=str, nargs='*', help='Services to activate', default=[])
    parser.add_argument('--adapters', metavar='N', type=str, nargs='*', help='Adapters to activate', default=[])
    parser.add_argument('--exclude', metavar='N', type=str, nargs='*', help='Adapters and Services to exclude',
                        default=[])

    try:
        args = parser.parse_args(args)
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    axonius_system = get_service()
    if args.all:
        assert len(args.services) == 0 and len(args.adapters) == 0
        args.services = [name for name, variable in axonius_system.get_all_plugins()]
        args.adapters = [name for name, variable in axonius_system.get_all_adapters()]

    if args.exclude:
        for name in args.exclude:
            if name not in args.services and name not in args.adapters:
                raise ValueError(f'Excluded name {name} not found')
        args.services = [name for name in args.services if name not in args.exclude]
        args.adapters = [name for name in args.adapters if name not in args.exclude]

    axonius_system.take_process_ownership()
    if args.pull_base_image:
        assert args.mode in ('up', 'build')
        args.hard = True
    if args.hard:
        assert args.mode in ('up', 'build')
        args.rebuild = True
    if args.mode in ('up', 'build'):
        axonius_system.pull_base_image(args.pull_base_image)
        axonius_system.build_libs(args.hard)
    if args.mode == 'up':
        print(f'Starting system and {args.adapters + args.services}')
        mode = 'prod' if args.prod else ''
        if args.restart:
            # clear old containers if exists...
            axonius_system.remove_plugin_containers(args.adapters, args.services)

        # Optimization - async build first
        axonius_system.build(True, args.adapters, args.services, 'prod' if args.prod else '', args.rebuild)

        axonius_system.start_and_wait(mode, args.restart, hard=args.hard, skip=args.skip)
        axonius_system.start_plugins(args.adapters, args.services, mode, args.restart, hard=args.hard, skip=args.skip)
    elif args.mode == 'down':
        assert not args.restart and not args.rebuild and not args.skip and not args.prod
        print(f'Stopping system and {args.adapters + args.services}')
        axonius_system.stop_plugins(args.adapters, args.services, should_delete=False)
        axonius_system.stop(should_delete=False)
    else:
        assert not args.restart and not args.skip
        print(f'Building system and {args.adapters + args.services}')
        axonius_system.build(True, args.adapters, args.services, 'prod' if args.prod else '', args.rebuild, args.hard)


def service_entry_point(target, args):
    parser = argparse.ArgumentParser(description='Axonius system startup', usage="""
{name} {target} [-h] name {up,down,build} [--prod] [--restart] [--rebuild] [--hard]
"""[1:-1].replace('{name}', os.path.basename(__file__)).replace('{target}', target))
    parser.add_argument('name')
    parser.add_argument('mode', choices=['up', 'down', 'build'])
    parser.add_argument('--prod', type=str2bool, nargs='?', const=True, default=False, help='Prod Mode')
    parser.add_argument('--restart', type=str2bool, nargs='?', const=True, default=False,
                        help='Restart container')
    parser.add_argument('--rebuild', type=str2bool, nargs='?', const=True, default=False, help='Rebuild Image')
    parser.add_argument('--hard', type=str2bool, nargs='?', const=True, default=False,
                        help='Rebuild Image after rebuilding axonius-libs')

    try:
        args = parser.parse_args(args)
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    adapters = []
    services = []

    if target == 'adapter':
        adapters.append(args.name)
    else:
        services.append(args.name)

    axonius_system = get_service()
    if args.hard:
        assert args.mode in ('up', 'build')
        axonius_system.build_libs(True)
        args.rebuild = True
    if args.mode == 'up':
        print(f'Starting {args.name}')
        axonius_system.start_plugins(adapters, services, 'prod' if args.prod else '', args.restart, args.rebuild,
                                     args.hard)
    elif args.mode == 'down':
        assert not args.restart and not args.rebuild
        print(f'Stopping {args.name}')
        axonius_system.stop_plugins(adapters, services, should_delete=False)
    else:
        assert not args.restart
        print(f'Building {args.name}')
        axonius_system.build(False, adapters, services, 'prod' if args.prod else '', args.rebuild, args.hard)


def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


class AutoFlush(object):
    def __init__(self):
        self._write = sys.stdout.write

    def write(self, text):
        self._write(text)
        sys.stdout.flush()

    def __enter__(self):
        sys.stdout.write = self.write

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.write = self._write


if __name__ == '__main__':
    with AutoFlush():
        main()
