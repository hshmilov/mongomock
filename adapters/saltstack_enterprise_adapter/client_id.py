from saltstack_enterprise_adapter.consts import DEFAULT_CONFIG_NAME


def get_client_id(client_config):
    config_params = (client_config['domain'],
                     client_config['username'],
                     client_config.get('config_name', DEFAULT_CONFIG_NAME))
    return '_'.join(filter(None, config_params))
