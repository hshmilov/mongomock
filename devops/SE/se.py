"""
System engineering common tasks.
"""
import sys
import os
import argparse

from axonius.consts.plugin_subtype import PluginSubtype
from testing.services.plugins.aggregator_service import AggregatorService
from testing.services.plugins.core_service import CoreService
from testing.services.plugins.static_correlator_service import StaticCorrelatorService
from testing.services.plugins.static_users_correlator_service import StaticUsersCorrelatorService


def main(args):
    parser = argparse.ArgumentParser(description='Axonius SE Panel', usage='''
    {name} list / fetch --adapter [plugin_unique_name] - control adapter
    {name} sc [run] - control static correlator   
    '''.format(name=os.path.basename(__file__)))
    parser.add_argument('component', choices=['adapter', 'sc'])
    parser.add_argument('action')
    parser.add_argument('--adapter', default=None)

    try:
        args = parser.parse_args(args)
    except AttributeError:
        print(parser.usage)
        return 1

    ag = AggregatorService()
    core = CoreService()
    sc = StaticCorrelatorService()
    scu = StaticUsersCorrelatorService()

    if args.component == 'adapter':
        if args.action == 'list':
            for plugin_unique_name, plugin_dict in core.get_registered_plugins().json().items():
                plugin_subtype = plugin_dict.get('plugin_subtype')
                if plugin_subtype in [PluginSubtype.ScannerAdapter.name, PluginSubtype.AdapterBase.name]:
                    print(f'{plugin_unique_name} - {plugin_subtype}')
        elif args.action == 'fetch':
            plugin_unique_name = args.adapter
            assert plugin_unique_name, parser.usage

            print(f'Fetching & Rebuilding db (Blocking) for {plugin_unique_name}...')
            ag.query_devices(plugin_unique_name)
        else:
            print(parser.usage)
            return 1
    elif args.component == 'sc':
        if args.action == 'run':
            print('Running static correlator..')
            sc.correlate(True)
            print('Running static users correlator..')
            scu.correlate(True)
        else:
            print(parser.usage)
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
