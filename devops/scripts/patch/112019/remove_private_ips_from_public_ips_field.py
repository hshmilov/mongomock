import sys

import ipaddress

from axonius.entities import EntityType
from testing.services.plugins.aggregator_service import AggregatorService


def main():
    aggregator = AggregatorService()
    devices_db = aggregator._entity_db_map[EntityType.Devices]

    try:
        state, plugin_unique_name = sys.argv[1], sys.argv[2]
    except Exception:
        print(f'Usage: {sys.argv[0]} dry/wet [plugin_unique_name]')
        return -1

    if plugin_unique_name == 'all':
        query = {'adapters.data.public_ips': {'$exists': True}}
    else:
        query = {
            'adapters': {
                '$elemMatch': {
                    'plugin_unique_name': plugin_unique_name,
                    'data.public_ips': {'$exists': True}
                }
            }
        }

    cursor = devices_db.find(
        query,
        projection={
            'adapters.data.public_ips': 1,
            'adapters.data.public_ips_raw': 1,
            'adapters.plugin_unique_name': 1,
            'adapters.quick_id': 1
        }
    )
    cursor_len = cursor.count()
    found_entities = 0
    for i, device_raw in enumerate(cursor):
        if i and (i % 1000 == 0):
            print(f'Parsed {i} / {cursor_len}')
        for adapter_raw in device_raw['adapters']:
            if plugin_unique_name == 'all' or adapter_raw['plugin_unique_name'] == plugin_unique_name:
                new_ips = []
                new_ips_raw = []
                did_change = False
                quick_id = adapter_raw['quick_id']
                public_ips = adapter_raw['data'].get('public_ips')
                for ip in (public_ips or []):
                    if ipaddress.ip_address(ip).is_private:
                        print(f'Going to remove {ip} from {quick_id}')
                        did_change = True
                        found_entities += 1
                    else:
                        new_ips.append(ip)
                        new_ips_raw.append(ipaddress.ip_address(ip)._ip)
                if did_change:
                    print(f'New ips: {new_ips}, New ips_raw: {new_ips_raw}')
                    if state == 'wet':
                        if new_ips:
                            devices_db.update_one(
                                {'adapters.quick_id': quick_id},
                                {'$set':
                                    {
                                        'adapters.$.data.public_ips': new_ips,
                                        'adapters.$.data.public_ips_raw': new_ips_raw
                                    }
                                 }
                            )
                        else:
                            devices_db.update_one(
                                {'adapters.quick_id': quick_id},
                                {
                                    '$unset':
                                        {
                                            'adapters.$.data.public_ips': 1,
                                            'adapters.$.data.public_ips_raw': 1
                                        }
                                }
                            )

    print(f'Fixed {found_entities} entities.')


if __name__ == '__main__':
    sys.exit(main())
