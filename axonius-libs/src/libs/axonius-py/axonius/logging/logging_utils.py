from collections import OrderedDict


def get_configurable_config_to_log(config_schema: dict, config: dict):
    """
    Takes a config and returns this config so that we can log it. It does not print irrelevant things (like files)
    and removes sensitive information.
    :param config_schema:
    :param config:
    :return:
    """
    config_to_log = OrderedDict()
    if config_schema:
        for item in (config_schema.get('items') or []):
            item_name = item.get('name') or 'unknown_name'
            item_type = item.get('type') or 'unknown_type'
            item_format = item.get('format')

            if str(item_format).lower() == 'password':
                config_to_log[item_name] = '<deducted>'
            elif item_type in ['bool', 'integer', 'number']:
                config_to_log[item_name] = config.get(item_name)
            elif item_type == 'array':
                if isinstance(config.get(item_name), list):
                    config_to_log[item_name] = get_configurable_config_to_log(item, config.get(item_name) or {})
                else:
                    config_to_log[item_name] = '<array of type dict>'
            else:
                config_to_log[item_name] = f'<format: {item_type}>'

    return config_to_log
