from services.axonius_service import AxoniusService


def main():
    ax = AxoniusService()
    adapters = ax.get_all_adapters()
    for adapter in adapters:
        name, cls = adapter
        instance = cls()
        try:
            ax.db.plugins.get_plugin_settings(instance.plugin_name).configurable_configs.update_config(
                'AdapterBase',
                {
                    'last_fetched_threshold_hours': 0,
                    'user_last_seen_threshold_hours': 0
                }
            )
        except Exception as e:
            print(f'Failed to set for {name}: {e}')


if __name__ == '__main__':
    main()
