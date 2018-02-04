import argparse
import os
import sys

from services.axonius_service import get_service


def main():
    parser = argparse.ArgumentParser(description='Axonius system startup', usage="""
{name} [-h] {system,adapter,plugin} [<args>]
       {name} system {up,down} [--all] [--prod] [--restart]
                                [--plugins [N [N ...]]] [--adapters [N [N ...]]]
       {name} {adapter,plugin} [-h] {up,down} name [--prod] [--restart]
"""[1:].replace('{name}', os.path.basename(__file__)))
    parser.add_argument('target', choices=['system', 'adapter', 'plugin'])

    try:
        args = parser.parse_args(sys.argv[1:2])
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    if args.target == 'system':
        system_entry_point(sys.argv[2:])
    else:
        service_entry_point(args.target, sys.argv[2:])


def system_entry_point(args):
    parser = argparse.ArgumentParser(description='Axonius system startup', usage="""
{name} system {up,down} [--all] [--prod] [--restart]
                                [--plugins [N [N ...]]] [--adapters [N [N ...]]]"""[1:].replace(
        '{name}', os.path.basename(__file__)))
    parser.add_argument('mode', choices=['up', 'down'])
    parser.add_argument('--all', type=str2bool, nargs='?', const=True, default=False, help='All adapters and plugins')
    parser.add_argument('--prod', type=str2bool, nargs='?', const=True, default=False, help='Production Mode')
    parser.add_argument('--restart', '-r', type=str2bool, nargs='?', const=True, default=False,
                        help='Restart container')
    parser.add_argument('--plugins', metavar='N', type=str, nargs='*', help='Plugins to activate', default=[])
    parser.add_argument('--adapters', metavar='N', type=str, nargs='*', help='Adapters to activate', default=[])

    try:
        args = parser.parse_args(args)
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    if args.all:
        if not args.plugins:
            args.plugins.extend(['watch', 'static_correlator', 'execution', 'dns_conflicts',
                                 'careful_execution_correlator', 'general_info'])
        if not args.adapters:
            args.adapters.extend(['ad', 'aws', 'cisco', 'epo', 'esx', 'jamf', 'nessus', 'nexpose', 'puppet', 'qualys',
                                  'qualys_scans', 'sentinelone', 'splunk_nexpose', 'symantec'])

    axonius_system = get_service()
    axonius_system.take_process_ownership()
    if args.mode == 'up':
        print(f'Starting system and {args.adapters + args.plugins}')
        mode = 'prod' if args.prod else ''
        if args.restart:
            # clear old containers if exists...
            axonius_system.remove_plugin_containers(args.adapters, args.plugins)
        axonius_system.start_and_wait(mode, args.restart)
        axonius_system.start_plugins(args.adapters, args.plugins, mode, args.restart)
    else:
        assert not args.restart
        print(f'Stopping system and {args.adapters + args.plugins}')
        axonius_system.stop_plugins(args.adapters, args.plugins, should_delete=False)
        axonius_system.stop(should_delete=False)


def service_entry_point(target, args):
    parser = argparse.ArgumentParser(description='Axonius system startup', usage="""
{name} {target} [-h] {up,down} name [--prod] [--restart]"""[1:].replace('{name}', os.path.basename(__file__)).replace(
                                     '{target}', target))
    parser.add_argument('mode', choices=['up', 'down'])
    parser.add_argument('--prod', type=str2bool, nargs='?', const=True, default=False, help='Production Mode')
    parser.add_argument('--restart', '-r', type=str2bool, nargs='?', const=True, default=False,
                        help='Restart container')
    parser.add_argument('name')

    try:
        args = parser.parse_args(args)
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    adapters = []
    plugins = []

    if target == 'adapter':
        adapters.append(args.name)
    else:
        plugins.append(args.name)

    axonius_system = get_service()
    if args.mode == 'up':
        print(f'Starting {args.name}')
        axonius_system.start_plugins(adapters, plugins, 'prod' if args.prod else '', args.restart)
    else:
        assert not args.restart
        print(f'Stopping {args.name}')
        axonius_system.stop_plugins(adapters, plugins, should_delete=False)


def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


if __name__ == '__main__':
    main()
