from zscaler_adapter.consts import DEFAULT_DOMAIN


def get_client_id(client_config):
    return '_'.join((client_config.get('domain') or DEFAULT_DOMAIN,
                     client_config.get('username')))
