def get_client_id(client_config):
    host = client_config['smc_host']
    username = client_config['username']
    return f'{host}_{username}'
