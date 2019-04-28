import pymongo
import sys
import os
from collections import defaultdict

from axonius.entities import EntityType
from testing.services.plugins.aggregator_service import AggregatorService

MARKER = '/home/ubuntu/2_3_fix_dups.marker'


def process_device(device, entity_type: EntityType) -> bool:
    """
    :return: whether or not to delete the device
    """

    # If there's a weird internaxonid
    # yes, this will also take old devices as casualties

    # Actually, let's try without this
    # iaid = device['internal_axon_id']
    # if not any(iaid == get_preferred_internal_axon_id(adapter['plugin_unique_name'], adapter['data']['id'],
    #                                                   entity_type)
    #            for adapter in device['adapters']):
    #     return True

    # group by adapter name
    by_plugin_name = defaultdict(list)
    for adapter in device['adapters']:
        by_plugin_name[adapter['plugin_name']].append(adapter)

    # now, for some heuristics

    ADs = by_plugin_name.get('active_directory_adapter')
    if not ADs:
        return False

    if any(adapter['data'].get('scanner') for adapter in ADs):
        # if any AD is a scanner, whoops...
        return True

    AD_ids = [x['data']['id'] for x in ADs]
    if len(AD_ids) != len(set(AD_ids)):
        # if not all AD ids are unique, whoops...
        return True

    for adapter in device['adapters']:
        if adapter['plugin_name'] != 'active_directory_adapter':
            if 'dns_resolve_status' in adapter['data']:
                # this means that AD data has leaked into other devices, delete it
                return True

    return False


def main(wet):
    print(f'Starting patch {sys.argv[0]} wet: {wet}')
    if os.path.exists(MARKER):
        print(f'Marker exists! Exiting')
        return 0
    with open(MARKER, 'wt') as f:
        f.write('marker')
    aggregator = AggregatorService()
    for entity_type in EntityType:
        entities_db = aggregator._entity_db_map[entity_type]
        entities = [x['_id']
                    for x
                    in entities_db.find({
                        'adapters.plugin_name': 'active_directory_adapter'
                    }) if process_device(x, entity_type)]
        print(f'Found {len(entities)} of type {entity_type}')
        if wet:
            to_fix = [pymongo.operations.DeleteOne({
                '_id': x
            }) for x in entities]
            entities_db.bulk_write(to_fix, ordered=False)


if __name__ == '__main__':
    try:
        _, wet = sys.argv
    except ValueError:
        print(f'usage: {sys.argv[0]} wet|dry')
        sys.exit(-1)
    sys.exit(main(wet == 'wet'))
