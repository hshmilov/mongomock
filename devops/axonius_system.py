import argparse
import os
import sys


try:
    import axonius
except (ModuleNotFoundError, ImportError):
    # if not in path...
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'plugins', 'axonius-libs', 'src', 'libs',
                                 'axonius-py'))


try:
    from services.axonius_service import get_service
except (ModuleNotFoundError, ImportError):
    # if not in path...
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'testing'))
    from services.axonius_service import get_service


def main():
    parser = argparse.ArgumentParser(description='Axonius system startup', usage="""
{name} [-h] {system,adapter,plugin} [<args>]
       {name} system [-h] {up,down,build} [--all] [--debug] [--restart] [--rebuild] [--skip]
                                [--plugins [N [N ...]]] [--adapters [N [N ...]]]
       {name} {adapter,plugin} [-h] {up,down,build} name [--debug] [--restart] [--rebuild]
       {name} ls
"""[1:].replace('{name}', os.path.basename(__file__)))
    parser.add_argument('target', choices=['system', 'adapter', 'plugin', 'ls'])

    try:
        args = parser.parse_args(sys.argv[1:2])
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    if args.target == 'system':
        system_entry_point(sys.argv[2:])
    elif args.target == 'ls':
        axonius_system = get_service()
        print('Core Plugins:')
        for service in axonius_system.axonius_services:
            print(f'    {service.container_name}')
        print('Plugins:')
        for name, _ in axonius_system.get_all_plugins():
            print(f'    {name}')
        print('Adatpers:')
        for name, _ in axonius_system.get_all_adapters():
            print(f'    {name}')
    else:
        service_entry_point(args.target, sys.argv[2:])


def system_entry_point(args):
    parser = argparse.ArgumentParser(description='Axonius system startup', usage="""
{name} system [-h] {up,down,build} [--all] [--debug] [--restart] [--rebuild] [--skip]
                                [--plugins [N [N ...]]] [--adapters [N [N ...]]]"""[1:].replace(
        '{name}', os.path.basename(__file__)))
    parser.add_argument('mode', choices=['up', 'down', 'build'])
    parser.add_argument('--all', type=str2bool, nargs='?', const=True, default=False, help='All adapters and plugins')
    parser.add_argument('--debug', type=str2bool, nargs='?', const=True, default=False, help='Debug Mode')
    parser.add_argument('--restart', '-r', type=str2bool, nargs='?', const=True, default=False,
                        help='Restart container')
    parser.add_argument('--rebuild', type=str2bool, nargs='?', const=True, default=False, help='Rebuild Image')
    parser.add_argument('--skip', type=str2bool, nargs='?', const=True, default=False,
                        help='Skip already up containers')
    parser.add_argument('--plugins', metavar='N', type=str, nargs='*', help='Plugins to activate', default=[])
    parser.add_argument('--adapters', metavar='N', type=str, nargs='*', help='Adapters to activate', default=[])

    try:
        args = parser.parse_args(args)
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    axonius_system = get_service()
    if args.all:
        if args.mode == 'build':
            # Build *all* docker images
            assert len(args.plugins) == 0 and len(args.adapters) == 0
            args.plugins = [name for name, variable in axonius_system.get_all_plugins()]
            args.adapters = [name for name, variable in axonius_system.get_all_adapters()]
        else:
            # when setting up the "standard system" use this hand-coded set of default plugins and adapters
            if not args.plugins:
                args.plugins.extend(['watch', 'static_correlator', 'execution', 'dns_conflicts',
                                     'careful_execution_correlator', 'general_info'])
            if not args.adapters:
                args.adapters.extend(['ad', 'aws', 'cisco', 'csv', 'epo', 'eset', 'fortigate', 'esx', 'jamf', 'nessus',
                                      'nexpose', 'puppet', 'qualys', 'qualys_scans', 'sentinelone', 'splunk_nexpose',
                                      'symantec'])

    axonius_system.take_process_ownership()
    if args.mode == 'up':
        print(f'Starting system and {args.adapters + args.plugins}')
        mode = 'debug' if args.debug else ''
        if args.restart:
            # clear old containers if exists...
            axonius_system.remove_plugin_containers(args.adapters, args.plugins)

        # Optimization - async build first
        axonius_system.build(True, args.adapters, args.plugins, 'debug' if args.debug else '', args.rebuild)

        axonius_system.start_and_wait(mode, args.restart, skip=args.skip)
        axonius_system.start_plugins(args.adapters, args.plugins, mode, args.restart, skip=args.skip)
    elif args.mode == 'down':
        assert not args.restart and not args.rebuild and not args.skip and not args.debug
        print(f'Stopping system and {args.adapters + args.plugins}')
        axonius_system.stop_plugins(args.adapters, args.plugins, should_delete=False)
        axonius_system.stop(should_delete=False)
    else:
        assert not args.restart and not args.skip
        print(f'Building system and {args.adapters + args.plugins}')
        axonius_system.build(True, args.adapters, args.plugins, 'debug' if args.debug else '', args.rebuild)


def service_entry_point(target, args):
    parser = argparse.ArgumentParser(description='Axonius system startup', usage="""
{name} {target} [-h] {up,down,build} name [--debug] [--restart] [--rebuild]
"""[1:-1].replace('{name}', os.path.basename(__file__)).replace('{target}', target))
    parser.add_argument('mode', choices=['up', 'down', 'build'])
    parser.add_argument('--debug', type=str2bool, nargs='?', const=True, default=False, help='Debug Mode')
    parser.add_argument('--restart', '-r', type=str2bool, nargs='?', const=True, default=False,
                        help='Restart container')
    parser.add_argument('--rebuild', type=str2bool, nargs='?', const=True, default=False, help='Rebuild Image')
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
        axonius_system.start_plugins(adapters, plugins, 'debug' if args.debug else '', args.restart, args.rebuild)
    elif args.mode == 'down':
        assert not args.restart and not args.rebuild
        print(f'Stopping {args.name}')
        axonius_system.stop_plugins(adapters, plugins, should_delete=False)
    else:
        assert not args.restart
        print(f'Building {args.name}')
        axonius_system.build(False, adapters, plugins, 'debug' if args.debug else '', args.rebuild)


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
