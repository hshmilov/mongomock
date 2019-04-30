from alertlogic_adapter.consts import DEFAULT_DOMAIN


def get_client_id(client_config):
    return (client_config.get('domain') or DEFAULT_DOMAIN) + '_' + client_config['apikey'][:4]
