from testing.services.plugins import aggregator_service


# pylint: disable=too-many-nested-blocks
def main():
    core = aggregator_service.AggregatorService().db.client['core']
    db = aggregator_service.AggregatorService().db.client['aggregator']
    devices_raw_data_average_size = dict()
    users_raw_data_average_size = dict()
    adapter_names = [adapter for adapter in core['configs'].find({}).distinct('plugin_name') if 'adapter' in adapter]
    for collection in ['devices_db', 'users_db']:
        for adapter_name in adapter_names:
            raw_data_total = 0
            num_of_devices = 0
            for device in db[collection].find({'adapters.plugin_name': adapter_name}).limit(1000):
                for adapter in device.get('adapters') or []:
                    if adapter.get('plugin_name') == adapter_name:
                        adapter_raw = (adapter.get('data') or {}).get('raw')
                        if adapter_raw:
                            raw_data_total += len(str(adapter_raw))
                            num_of_devices += 1
            if num_of_devices:
                raw_data_average = raw_data_total / num_of_devices
                if 'users' in collection:
                    users_raw_data_average_size[adapter_name] = raw_data_average
                else:
                    devices_raw_data_average_size[adapter_name] = raw_data_average

    overall_raw_data = 0
    print(f'-- devices data --')
    for adapter_name, avg_size in devices_raw_data_average_size.items():
        num = db['devices_db'].count_documents({'adapters.plugin_name': adapter_name})
        avg_size_mb = round(avg_size / (1024 ** 2), 6)
        total = avg_size_mb * num
        overall_raw_data += total
        print(f'Adapter {adapter_name} has {num} devices with an '
              f'average raw data size of {avg_size_mb}mb. Total size is {total}mb')

    print(f'Overall size for devices raw data in mb: {overall_raw_data}')

    overall_raw_data = 0
    print(f'-- users data --')
    for adapter_name, avg_size in users_raw_data_average_size.items():
        num = db['users_db'].count_documents({'adapters.plugin_name': adapter_name})
        avg_size_mb = round(avg_size / (1024 ** 2), 6)
        total = avg_size_mb * num
        overall_raw_data += total
        print(f'Adapter {adapter_name} has {num} users with an '
              f'average raw data size of {avg_size_mb}mb. Total size is {total}mb')

    print(f'Overall size for devices raw data in mb: {overall_raw_data}')


if __name__ == '__main__':
    exit(main())
