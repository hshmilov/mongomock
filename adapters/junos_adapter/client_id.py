def get_client_id(client_config):
    if not client_config.get('port'):
        client_config['port'] = 22
    return ':'.join([client_config['host'], str(client_config['port'])])
