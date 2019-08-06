#!/usr/bin/env python3

"""
This scripts allows you to hide or show adapters in the adapters page.
This doesn't affect their behavior, and if they have credentials, they will still bring devices.

Usage example:

1. dry running with plugin_unique_name

$ python devops/scripts/maintenance_tools/adapter_hider.py --hide aws_adapter_0 --dry
	Matched aws_adapter_0, is displayed (node 969980d2ce004df2b8fa8e7d21f0f011)

2. dry running with plugin_name

$ python devops/scripts/maintenance_tools/adapter_hider.py --hide aws_adapter --dry
	Matched aws_adapter_0, is displayed (node 969980d2ce004df2b8fa8e7d21f0f011)
	Matched aws_adapter_1, is displayed (node 969980d2ce004df2b8fa8e7d21f0f012)

3. hiding by plugin_name

$ python devops/scripts/maintenance_tools/adapter_hider.py --hide aws_adapter
    Matched 2, modified 2

4. dry running, verified change

$ python devops/scripts/maintenance_tools/adapter_hider.py --hide aws_adapter --dry
	Matched aws_adapter_0, is hidden (node 969980d2ce004df2b8fa8e7d21f0f011)
	Matched aws_adapter_1, is hidden (node 969980d2ce004df2b8fa8e7d21f0f012)

5. restoring

$ python devops/scripts/maintenance_tools/adapter_hider.py --restore aws_adapter
	Matched 2, modified 2

6. verifying

$ python devops/scripts/maintenance_tools/adapter_hider.py --hide aws_adapter --dry
	Matched aws_adapter_0, is displayed (node 969980d2ce004df2b8fa8e7d21f0f011)
	Matched aws_adapter_1, is displayed (node 969980d2ce004df2b8fa8e7d21f0f012)

"""

import argparse
import sys

from pymongo.collection import Collection

from axonius.consts.plugin_consts import PLUGIN_NAME, PLUGIN_UNIQUE_NAME, CORE_UNIQUE_NAME
from services.plugins.mongo_service import MongoService


class HiderArgs(argparse.Namespace):
    hide: str
    restore: str
    dry: bool


def build_matching_query(name: str) -> dict:
    """
    Builds a query that matches either plugin_unique_name or plugin_name
    :param name: the plugin_unique_name or plugin_name to match
    :return: a query suitable for matching those documents in core.configs in mongo
    """
    return {
        '$or': [
            {
                PLUGIN_UNIQUE_NAME: name,
            },
            {
                PLUGIN_NAME: name
            }
        ]
    }


def main(args: HiderArgs):
    mongo_service = MongoService()
    configs_collection: Collection = mongo_service.client[CORE_UNIQUE_NAME]['configs']
    plugin_name = args.hide or args.restore
    hidden_state = bool(args.hide)

    if args.dry:
        cursor = configs_collection.find(build_matching_query(plugin_name))
        for adapter in cursor:
            if adapter.get('hidden'):
                t = 'hidden'
            else:
                t = 'displayed'
            print(f'Matched {adapter[PLUGIN_UNIQUE_NAME]}, is {t} (node {adapter["node_id"]})')
        return

    result = configs_collection.update_many(build_matching_query(plugin_name),
                                            {
                                                '$set': {
                                                    'hidden': hidden_state
                                                }})
    print(f'Matched {result.matched_count}, modified {result.modified_count}')


def parse_args() -> HiderArgs:
    """
    Returns the value to set 'hidden' to, and the plugin_unique_name/plugin_name to alter.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--hide', type=str, )
    parser.add_argument('--restore', type=str)
    parser.add_argument('--dry', action='store_true')

    args = HiderArgs()
    parser.parse_args(namespace=args)
    if (not args.hide and not args.restore) or (args.hide and args.restore):
        print('You need to supply either --hide or --restore, not both')
        sys.exit(1)
    return args


if __name__ == '__main__':
    main(parse_args())
