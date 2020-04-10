from testing.services.plugins import core_service


def main():
    db = core_service.CoreService().db.client

    # Get all adapter names
    all_adapters_names = list(db['core']['configs'].find({'plugin_type': 'Adapter'}).distinct('plugin_name'))

    for plugin_name in all_adapters_names:
        original_configurable_configs = list(db[f'{plugin_name}_0']['configurable_configs'].find({}))
        if not original_configurable_configs:
            # No settings for master adapter
            continue

        original_adapter_settings = list(db[f'{plugin_name}_0']['adapter_settings'].find({}))

        i = 1
        while True:
            new_db = db[f'{plugin_name}_{i}']
            if not list(new_db['configurable_configs'].find({})):
                # no such db
                break

            new_db['configurable_configs'].drop()
            new_db['configurable_configs'].insert_many(original_configurable_configs)

            if original_adapter_settings:
                try:
                    new_db['adapter_settings'].drop()
                except Exception:
                    # This could not exist and it is fine
                    pass
                new_db['adapter_settings'].insert_many(original_adapter_settings)
            i += 1

    print(f'Done migrating')


if __name__ == '__main__':
    exit(main())
