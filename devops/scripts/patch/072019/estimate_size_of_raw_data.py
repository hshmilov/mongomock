from testing.services.plugins import aggregator_service


def main():
    db = aggregator_service.AggregatorService().db.client['aggregator']
    overall_all_storage_size = 0
    overall_raw_storage_size = 0
    for collection in ['devices_db', 'users_db', 'historical_devices_db_view', 'historical_users_db_view']:
        try:
            size_of_all_data = 0
            size_of_raw_data = 0
            estimated_storage_size = db.command('collstats', collection)['storageSize']
            for document in db[collection].find({}).limit(1000):
                size_of_all_data += len(str(document))
                for adapter in document.get('adapters') or []:
                    adapter_raw = (adapter.get('data') or {}).get('raw')
                    if adapter_raw:
                        size_of_raw_data += len(str(adapter_raw))

            overall_all_storage_size += estimated_storage_size
            overall_raw_storage_size += (size_of_raw_data / size_of_all_data) * estimated_storage_size
        except Exception as e:
            print(f'Failed to estimate size of raw data for collection {collection}: {str(e)}')

    print(f'Size of all adapters data: {overall_all_storage_size / (1024 ** 2)} mb')
    print(f'Size of adapters raw_data: {overall_raw_storage_size / (1024 ** 2)} mb')


if __name__ == '__main__':
    exit(main())
