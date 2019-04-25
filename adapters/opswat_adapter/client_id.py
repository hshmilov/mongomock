def get_client_id(client_config):
    return (client_config.get('domain') or '') + '_' + client_config['client_id']
