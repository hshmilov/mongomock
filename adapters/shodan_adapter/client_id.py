def get_client_id(client_config):
    return client_config.get('user_id') or client_config['cidr'].split(',')[0]
