"""
Adds a new adapterdata to a set of devices.
This is useful if we need a boilerplate for adding fake adapterdevices for some reason (like demo's).
"""
import datetime
import sys
import uuid

from axonius.entities import EntityType
from testing.services.plugins import aggregator_service


# pylint: disable=protected-access
def main():
    devices_db = aggregator_service.AggregatorService()._entity_db_map[EntityType.Devices]
    for i, device in enumerate(devices_db.find({})):
        ad_adapter = [adapter for adapter in device['adapters'] if adapter['plugin_name'] == 'active_directory_adapter']
        pa_adapter = [adapter for adapter in device['adapters'] if adapter['plugin_name'] == 'paloalto_cortex_adapter']
        if ad_adapter and not pa_adapter:
            ad_adapter = ad_adapter[0]
            new_device_data = dict()
            for field in ['hostname', 'name', 'network_interfaces', 'domain', 'last_seen']:
                if ad_adapter['data'].get(field):
                    new_device_data[field] = ad_adapter['data'][field]

            new_device_data.update(
                {
                    'id': str(uuid.uuid4()),
                    'agent_id': str(uuid.uuid4()),
                    'customer_id': str(uuid.uuid4()),
                    'traps_id': str(uuid.uuid4()),
                    'agent_version': '5.0.5.2072',
                    'protection_status': False,
                    'is_vdi': False
                }
            )

            new_device = {
                'client_used': 'paloalto',
                'plugin_type': 'Adapter',
                'plugin_name': 'paloalto_cortex_adapter',
                'plugin_unique_name': 'paloalto_cortex_adapter_0',
                'type': 'entitydata',
                'accurate_for_datetime': datetime.datetime.now(),
                'data': new_device_data
            }
            device['adapter_list_length'] += 1
            device['adapters'].append(new_device)
            devices_db.update_one({'internal_axon_id': device['internal_axon_id']}, {'$set': device})
            print(f'Updated {i}')


if __name__ == '__main__':
    sys.exit(main())
