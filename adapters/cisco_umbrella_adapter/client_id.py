def get_client_id(client_config):
    return client_config.get('domain') or ('cloud' + '_' + client_config['network_api_key'])
