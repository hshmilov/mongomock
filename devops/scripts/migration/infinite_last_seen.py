from axonius.consts.plugin_consts import CONFIGURABLE_CONFIGS
from services.axonius_service import AxoniusService


def main():
    ax = AxoniusService()
    adapters = ax.get_all_adapters()
    for adapter in adapters:
        name, cls = adapter
        instance = cls()
        try:
            unique_name = instance.unique_name
            configs = ax.db.client[unique_name][CONFIGURABLE_CONFIGS]

            configs.update_one(filter={'config_name': 'AdapterBase'},
                               update={'$set': {'config.last_fetched_threshold_hours': 0,
                                                'config.user_last_seen_threshold_hours': 0}})
        except Exception as e:
            print(f'Failed to set for {name}: {e}')


if __name__ == '__main__':
    main()
