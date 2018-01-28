import argparse
import sys

from services.axonius_service import get_service


def main():
    parser = argparse.ArgumentParser(description='Axonius system startup')
    parser.add_argument('system', choices=['up', 'down'])
    parser.add_argument('--plugins', metavar='N', type=str, nargs='*', help='Plugins to activate', default=[])
    parser.add_argument('--adapters', metavar='N', type=str, nargs='*', help='Plugins to activate', default=[])

    try:
        args = parser.parse_args()
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    axonius_system = get_service()
    axonius_system.take_process_ownership()
    if args.system == 'up':
        axonius_system.start_and_wait()
        axonius_system.start_plugins(args.plugins + args.adapters)
    else:
        axonius_system.stop_plugins(args.adapters + args.plugins, should_delete=False)
        axonius_system.stop(should_delete=False)


if __name__ == '__main__':
    main()
