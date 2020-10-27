def get_client_id(client_config):
    client_id = f'{client_config.get("domain")}_{client_config.get("username")}'
    if client_config.get('username_domain'):
        client_id = f'{client_id}_{client_config.get("username_domain")}'
    return client_id
