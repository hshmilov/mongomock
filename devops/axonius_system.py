#!/usr/bin/env python3
import argparse
import sys
import traceback

from datetime import datetime

from pymongo.errors import PyMongoError

from conf_tools import get_customer_conf_json
from exclude_helper import ExcludeHelper
from services.axonius_service import get_service
import subprocess
import platform
import os

from services.standalone_services.mockingbird_service import MOCKINGBIRD_SERVICE
from axonius.consts.system_consts import (METADATA_PATH,
                                          AXONIUS_MOCK_DEMO_ENV_VAR,
                                          SYSTEM_CONF_PATH,
                                          CUSTOMER_CONF_PATH,
                                          NODE_MARKER_PATH,
                                          NODE_CONF_PATH,
                                          CORTEX_PATH)

from devops.scripts.watchdog import watchdog_main


def main(command):
    parser = argparse.ArgumentParser(description='Axonius system startup', usage="""
{name} [-h] {system,adapter,service} [<args>]
       {name} system [-h] {up,down,build,register} [--all] [--prod] [--restart] [--rebuild] [--hard] [--pull-base-image] [--skip]
                                [--services [N [N ...]]] [--adapters [N [N ...]]] [--exclude [N [N ...]]]
       {name} {adapter,service} [-h] name {up,down,build,quick_register} [--prod] [--restart] [--rebuild] [--hard] [--rebuild-libs]
       {name} ls
"""[1:].replace('{name}', os.path.basename(__file__)))
    parser.add_argument('target', choices=['system', 'adapter', 'service', 'standalone', 'ls'])

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
        for name, adapter in axonius_system.get_all_adapters():
            print(f'    {name}, {adapter().container_name}')
        print('Standalone services:')
        for name, _ in axonius_system.get_all_standalone_services():
            print(f'    {name}')
    else:
        service_entry_point(args.target, command[1:])


class ExtendAction(argparse.Action):

    def __call__(self, parser, namespace, values, option_string=None):
        items = getattr(namespace, self.dest) or []
        items.extend(values)
        setattr(namespace, self.dest, items)


def restart_watchdogs():
    watchdog_main.run_tasks('restart')


def stop_watchdogs():
    watchdog_main.run_tasks('stop')


def system_entry_point(args):
    parser = argparse.ArgumentParser(description='Axonius system startup', usage="""
{name} system [-h] {up,down,build} [--all] [--prod] [--restart] [--rebuild] [--hard] [--skip]
                                [--services [N [N ...]]] [--adapters [N [N ...]]] [--exclude [N [N ...]]]"""[1:].
                                     replace('{name}', os.path.basename(__file__)))
    parser.add_argument('mode', choices=['up', 'down', 'build', 'register', 'weave_recover'])
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
    internal_services = [service.service_name for service in axonius_system.axonius_services]
    if args.all:
        assert len(args.services) == 0 and len(args.adapters) == 0
        args.services = [name for name, variable in axonius_system.get_all_plugins() if name != 'diagnostics']
        args.adapters = [name for name, variable in axonius_system.get_all_adapters()]
        # standalone services shouldn't be raised as part of --all.

        if args.mode != 'down':
            args.exclude = process_exclude_from_config(args.exclude)

    for name in args.exclude:
        if name not in args.services and name not in args.adapters and name not in internal_services:
            raise ValueError(
                f'Excluded name {name} not found in services:{args.services} or in adapters: {args.adapters} '
                f'or in internal_services:{internal_services}')

    args.services = [name for name in args.services if name not in args.exclude]
    args.adapters = [name for name in args.adapters if name not in args.exclude]
    internal_services = [name for name in internal_services if name not in args.exclude]

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

    standalone_services = []
    if is_demo_instance():
        args.env.append(AXONIUS_MOCK_DEMO_ENV_VAR)
        standalone_services = [MOCKINGBIRD_SERVICE]

    system_config = get_customer_conf_json()

    if args.mode == 'up':
        print(f'Starting system and {args.adapters + args.services}')
        mode = 'prod' if args.prod else ''
        if args.restart:
            # clear old containers if exists...
            axonius_system.remove_plugin_containers(args.adapters, args.services)

        adapters_to_raise = args.adapters
        adapters_to_register = []

        # If the adapter count is low, don't bother doing quick register
        if len(args.adapters) > 10:
            print('Going to fast flow, only registering the adapters')
            adapters_to_register = adapters_to_raise
            adapters_to_raise = []

        # Optimization - async build first
        axonius_system.build(True, adapters_to_raise, args.services, [], 'prod' if args.prod else '', args.rebuild)
        print('finished building')

        axonius_system.start_and_wait(mode, args.restart, hard=args.hard, skip=args.skip, expose_db=args.expose_db,
                                      env_vars=args.env, internal_service_white_list=internal_services,
                                      system_config=system_config)
        print('finished start and wait')

        axonius_system.start_plugins(adapter_names=adapters_to_raise,
                                     plugin_names=args.services,
                                     standalone_services_names=standalone_services,
                                     mode=mode,
                                     allow_restart=args.restart,
                                     hard=args.hard,
                                     skip=args.skip,
                                     env_vars=args.env, system_config=system_config)
        now = datetime.now()
        if adapters_to_register:
            print(f'Starting to quick register at {now}')
        failed_quick_register_adapters = set()
        for adapter in adapters_to_register:
            print(f'Quick registering {adapter}')
            try:
                axonius_system.get_adapter(adapter).quick_register()
            except PyMongoError as e:
                tb = ''.join(traceback.format_tb(e.__traceback__))
                print(f'Failed quick registering {adapter} because of {e}, {tb}')
                print(f'Reverting to regular start due to mongo error')
                failed_quick_register_adapters = set(adapters_to_register)
                break
            except ImportError as e:
                print(f'Can\'t import {e.name} so not quick registering  {adapter}')
                failed_quick_register_adapters.add(adapter)
            except Exception as e:
                tb = ''.join(traceback.format_tb(e.__traceback__))
                print(f'Failed quick registering {adapter} because of {e}, {tb}')
                failed_quick_register_adapters.add(adapter)
        if adapters_to_register:
            print(f'Finished quick registering, took {(datetime.now() - now).total_seconds()} seconds')

        if failed_quick_register_adapters:
            # Fallback for failed quick register adapters
            axonius_system.start_plugins(adapter_names=list(failed_quick_register_adapters),
                                         plugin_names=args.services,
                                         standalone_services_names=standalone_services,
                                         mode=mode,
                                         allow_restart=args.restart,
                                         hard=args.hard,
                                         skip=args.skip,
                                         env_vars=args.env, system_config=system_config)

        restart_watchdogs()
    elif args.mode == 'down':
        assert not args.restart and not args.rebuild and not args.skip and not args.prod
        print(f'Stopping system and {args.adapters + args.services}')
        axonius_system.stop_plugins(args.adapters, args.services, [], should_delete=False)
        axonius_system.stop(should_delete=False)
        stop_watchdogs()
    elif args.mode == 'register':
        print(f'Registering system and {args.adapters + args.services}')
        axonius_system.register_unique_dns(system_base=True,
                                           adapter_names=args.adapters,
                                           plugin_names=args.services,
                                           standalone_services_names=standalone_services, system_config=system_config)
    elif args.mode == 'weave_recover':
        print(f'Starting weave recover')
        services = [name for name, variable in axonius_system.get_all_plugins() if name != 'diagnostics']
        adapters = [name for name, variable in axonius_system.get_all_adapters()]
        axonius_system.recover_weave_network(adapters, services, standalone_services)

    else:
        assert not args.restart and not args.skip
        print(f'Building system and {args.adapters + args.services}')
        axonius_system.build(True, args.adapters, args.services, [], 'prod' if args.prod else '', args.rebuild,
                             args.hard)


def process_exclude_from_config(exclude):
    conf_exclude = ExcludeHelper(SYSTEM_CONF_PATH).process_exclude([])
    conf_exclude = ExcludeHelper(CUSTOMER_CONF_PATH).process_exclude(conf_exclude)
    if NODE_MARKER_PATH.exists():
        conf_exclude = ExcludeHelper(NODE_CONF_PATH).process_exclude(conf_exclude)
    if 'linux' not in sys.platform.lower():
        conf_exclude.append('instance_control')
    return set(conf_exclude).union(exclude)


def is_demo_instance():
    try:
        customer_conf = get_customer_conf_json()
        return customer_conf.get('is_demo', False)
    except Exception:
        return False


def service_entry_point(target, args):
    parser = argparse.ArgumentParser(description='Axonius system startup', usage="""
{name} {target} [-h] name {up,down,build} [--prod] [--restart] [--rebuild] [--hard] [--rebuild-libs]
"""[1:-1].replace('{name}', os.path.basename(__file__)).replace('{target}', target))
    parser.add_argument('name')
    parser.add_argument('mode', choices=['up', 'down', 'build', 'register', 'quick_register'])
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

    services = []
    adapters = []
    standalone_services = []
    if target == 'adapter':
        adapters = [name for name, _ in axonius_system.get_all_adapters()] if args.name == 'all' else [args.name]
    elif target == 'service':
        services = [name for name, _ in axonius_system.get_all_plugins()] if args.name == 'all' else [args.name]
    elif target == 'standalone':
        standalone_services = [name for name, _ in axonius_system.get_all_standalone_services()] if \
            args.name == 'all' else [args.name]
    else:
        raise ValueError(f'Error, target {target} not found')

    if args.name == 'all':
        args.exclude = process_exclude_from_config(args.exclude)

    if args.exclude:
        services = [name for name in services if name not in args.exclude]
        adapters = [name for name in adapters if name not in args.exclude]
        standalone_services = [name for name in standalone_services if name not in args.exclude]

    system_config = get_customer_conf_json()
    axonius_system = get_service()
    if args.hard:
        assert args.mode in ('up', 'build')
        assert args.yes_hard is True, "--hard will delete all of your volumes! if you are sure, pass --yes-hard"
        args.rebuild = True
    if args.mode in ('up', 'build'):
        axonius_system.pull_base_image(args.pull_base_image)
        axonius_system.build_libs(args.rebuild_libs)
    if is_demo_instance():
        args.env.append(AXONIUS_MOCK_DEMO_ENV_VAR)

    if args.mode == 'quick_register':
        for adapter in adapters:
            print(f'Registering {adapter}')
            axonius_system.get_adapter(adapter).quick_register()
    elif args.mode == 'up':
        print(f'Starting {args.name}')
        axonius_system.start_plugins(adapters, services, standalone_services, 'prod' if args.prod else '',
                                     args.restart, args.rebuild, args.hard, env_vars=args.env,
                                     system_config=system_config)
    elif args.mode == 'down':
        assert not args.restart and not args.rebuild
        print(f'Stopping {args.name}')
        axonius_system.stop_plugins(adapters, services, standalone_services, should_delete=False)
    elif args.mode == 'register':
        print(f'Registering {args.name}')
        axonius_system.register_unique_dns(adapters, services, standalone_services, system_config=system_config)
    else:
        assert not args.restart
        print(f'Building {args.name}')
        axonius_system.build(False, adapters, services, standalone_services,
                             'prod' if args.prod else '', args.rebuild, args.hard)


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
    cmd_list = [f'{CORTEX_PATH}/install/metadata.sh', version]
    if platform.system() == 'Windows':
        cmd_list.insert(0, os.getenv(('PROGRAMW6432'
                                      if platform.architecture()[0] == '32bit'
                                      else 'PROGRAMFILES')) + r'\Git\bin\bash')
        return subprocess.check_output(cmd_list)
    return subprocess.check_output(cmd_list).decode()


if __name__ == '__main__':
    with AutoFlush():
        main(sys.argv[1:])
