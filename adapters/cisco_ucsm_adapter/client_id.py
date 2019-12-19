def get_client_id(client_config):
    domain = client_config['domain']
    username = client_config['username']
    return f'cucsm://{domain}_{username}'
