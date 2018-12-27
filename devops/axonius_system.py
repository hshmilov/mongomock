#!/usr/bin/env python3

import argparse
import os
import sys
from pathlib import Path

from axonius.consts.plugin_consts import AXONIOUS_SETTINGS_DIR_NAME
from exclude_helper import ExcludeHelper
from services.axonius_service import get_service
import subprocess

CORTEX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
METADATA_PATH = os.path.join(CORTEX_PATH, 'shared_readonly_files', '__build_metadata')
SYSTEM_CONF_PATH = Path(CORTEX_PATH) / 'system_conf.json'
CUSTOMER_CONF_RELATIVE_PATH = Path(AXONIOUS_SETTINGS_DIR_NAME) / 'customer_conf.json'
CUSTOMER_CONF_PATH = Path(CORTEX_PATH) / CUSTOMER_CONF_RELATIVE_PATH


def main(command):
    parser = argparse.ArgumentParser(description='Axonius system startup', usage="""
{name} [-h] {system,adapter,service} [<args>]
       {name} system [-h] {up,down,build} [--all] [--prod] [--restart] [--rebuild] [--hard] [--pull-base-image] [--skip]
                                [--services [N [N ...]]] [--adapters [N [N ...]]] [--exclude [N [N ...]]]
       {name} {adapter,service} [-h] name {up,down,build} [--prod] [--restart] [--rebuild] [--hard] [--rebuild-libs]
       {name} ls
"""[1:].replace('{name}', os.path.basename(__file__)))
    parser.add_argument('target', choices=['system', 'adapter', 'service', 'ls'])

    try:
        args = parser.parse_args(command[0:1])
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    if args.target == 'system':
        system_entry_point(command[1:])
    elif args.target == 'ls':
        axonius_system = get_service()
        print('Core Services:')
        for service in axonius_system.axonius_services:
            name = os.path.basename(service.service_dir)
            print(f'    {name}')
        print('Services:')
        for name, _ in axonius_system.get_all_plugins():
            print(f'    {name}')
        print('Adapters:')
        for name, _ in axonius_system.get_all_adapters():
            print(f'    {name}')
    else:
        service_entry_point(args.target, command[1:])


class ExtendAction(argparse.Action):

    def __call__(self, parser, namespace, values, option_string=None):
        items = getattr(namespace, self.dest) or []
        items.extend(values)
        setattr(namespace, self.dest, items)


def system_entry_point(args):
    parser = argparse.ArgumentParser(description='Axonius system startup', usage="""
{name} system [-h] {up,down,build} [--all] [--prod] [--restart] [--rebuild] [--hard] [--skip]
                                [--services [N [N ...]]] [--adapters [N [N ...]]] [--exclude [N [N ...]]]"""[1:].
                                     replace('{name}', os.path.basename(__file__)))
    parser.add_argument('mode', choices=['up', 'down', 'build'])
    parser.add_argument('--all', action='store_true', default=False, help='All adapters and services')
    parser.add_argument('--prod', action='store_true', default=False, help='Prod Mode')
    parser.add_argument('--restart', action='store_true', default=False, help='Restart container')
    parser.add_argument('--rebuild', action='store_true', default=False, help='Rebuild Image')
    parser.add_argument('--hard', action='store_true', default=False,
                        help='Rebuild Image after rebuilding axonius-libs and remove old volumes')
    parser.add_argument('--pull-base-image', action='store_true', default=False, help='Pull base image before rebuild')
    parser.add_argument('--skip', action='store_true', default=False, help='Skip already up containers')
    parser.add_argument('--services', metavar='N', type=str, nargs='*', help='Services to activate', default=[])
    parser.add_argument('--adapters', metavar='N', type=str, nargs='*', help='Adapters to activate', default=[])
    parser.add_argument('--exclude', metavar='N', type=str, nargs='*', action=ExtendAction,
                        help='Adapters and Services to exclude',
                        default=[])
    parser.add_argument('--expose-db', action='store_true', default=False,
                        help='Expose db port outside of this machine.')
    parser.add_argument('--version-name', default='',
                        help='Puts the version name in generated metadata.')
    parser.add_argument('--rebuild-libs', action='store_true', default=False, help='Rebuild axonius-libs first')
    parser.add_argument('--yes-hard', default=False, action='store_true')
    parser.add_argument('--env', metavar='N', type=str, nargs='*', action=ExtendAction,
                        help='environment vars to start the containers with',
                        default=[])

    try:
        args = parser.parse_args(args)
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    metadata_path = METADATA_PATH

    if not os.path.isfile(metadata_path):
        with open(metadata_path, 'wb') as f:
            f.write(get_metadata('none').encode())

    axonius_system = get_service()
    if args.all:
        assert len(args.services) == 0 and len(args.adapters) == 0
        args.services = [name for name, variable in axonius_system.get_all_plugins() if name != 'diagnostics']
        args.adapters = [name for name, variable in axonius_system.get_all_adapters()]

        conf_exclude = ExcludeHelper(SYSTEM_CONF_PATH).process_exclude([])
        conf_exclude = ExcludeHelper(CUSTOMER_CONF_PATH).process_exclude(conf_exclude)
        args.exclude = set(conf_exclude).union(args.exclude)

    for name in args.exclude:
        if name not in args.services and name not in args.adapters:
            raise ValueError(f'Excluded name {name} not found in {args.services} and {args.adapters}')

    args.services = [name for name in args.services if name not in args.exclude]
    args.adapters = [name for name in args.adapters if name not in args.exclude]

    axonius_system.take_process_ownership()
    if args.hard:
        assert args.mode in ('up', 'build')
        assert args.yes_hard is True, "--hard will delete all of your volumes! if you are sure, pass --yes-hard"
        args.rebuild = True
    if args.pull_base_image or args.rebuild_libs:
        assert args.mode in ('up', 'build')
    if args.mode in ('up', 'build'):
        axonius_system.pull_base_image(args.pull_base_image)
        axonius_system.build_libs(args.rebuild_libs)
    if args.mode == 'up':
        print(f'Starting system and {args.adapters + args.services}')
        axonius_system.create_network()
        mode = 'prod' if args.prod else ''
        if args.restart:
            # clear old containers if exists...
            axonius_system.remove_plugin_containers(args.adapters, args.services)

        # Optimization - async build first
        axonius_system.build(True, args.adapters, args.services, 'prod' if args.prod else '', args.rebuild)
        axonius_system.start_and_wait(mode, args.restart, hard=args.hard, skip=args.skip, expose_db=args.expose_db)
        axonius_system.start_plugins(args.adapters, args.services, mode, args.restart, hard=args.hard, skip=args.skip,
                                     env_vars=args.env)
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
{name} {target} [-h] name {up,down,build} [--prod] [--restart] [--rebuild] [--hard] [--rebuild-libs]
"""[1:-1].replace('{name}', os.path.basename(__file__)).replace('{target}', target))
    parser.add_argument('name')
    parser.add_argument('mode', choices=['up', 'down', 'build'])
    parser.add_argument('--prod', action='store_true', default=False, help='Prod Mode')
    parser.add_argument('--restart', action='store_true', default=False, help='Restart container')
    parser.add_argument('--rebuild', action='store_true', default=False, help='Rebuild Image')
    parser.add_argument('--hard', action='store_true', default=False, help='Removes old volume')
    parser.add_argument('--pull-base-image', action='store_true', default=False, help='Pull base image before rebuild')
    parser.add_argument('--rebuild-libs', action='store_true', default=False, help='Rebuild axonius-libs first')
    parser.add_argument('--yes-hard', default=False, action='store_true')
    parser.add_argument('--exclude', metavar='N', type=str, nargs='*', action=ExtendAction,
                        help='Adapters and Services to exclude',
                        default=[])
    parser.add_argument('--env', metavar='N', type=str, nargs='*', action=ExtendAction,
                        help='environment vars to start the containers with',
                        default=[])

    try:
        args = parser.parse_args(args)
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    axonius_system = get_service()

    if target == 'adapter':
        adapters = [name for name, _ in axonius_system.get_all_adapters()] if args.name == 'all' else [args.name]
        services = []
    else:
        services = [name for name, _ in axonius_system.get_all_plugins()] if args.name == 'all' else [args.name]
        adapters = []

    if args.exclude:
        services = [name for name in services if name not in args.exclude]
        adapters = [name for name in adapters if name not in args.exclude]

    axonius_system = get_service()
    if args.hard:
        assert args.mode in ('up', 'build')
        assert args.yes_hard is True, "--hard will delete all of your volumes! if you are sure, pass --yes-hard"
        args.rebuild = True
    if args.mode in ('up', 'build'):
        axonius_system.pull_base_image(args.pull_base_image)
        axonius_system.build_libs(args.rebuild_libs)
    if args.mode == 'up':
        print(f'Starting {args.name}')
        axonius_system.start_plugins(adapters, services, 'prod' if args.prod else '', args.restart, args.rebuild,
                                     args.hard, env_vars=args.env)
    elif args.mode == 'down':
        assert not args.restart and not args.rebuild
        print(f'Stopping {args.name}')
        axonius_system.stop_plugins(adapters, services, should_delete=False)
    else:
        assert not args.restart
        print(f'Building {args.name}')
        axonius_system.build(False, adapters, services, 'prod' if args.prod else '', args.rebuild, args.hard)


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


def get_metadata(version):
    cmd = f'{CORTEX_PATH}/install/metadata.sh {version}'
    return subprocess.check_output(cmd.split()).decode()


if __name__ == '__main__':
    with AutoFlush():
        main(sys.argv[1:])
