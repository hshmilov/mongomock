def get_client_id(client_config):
    return '_'.join([client_config['domain'],
                     client_config['login_provider'],
                     client_config['username']])
