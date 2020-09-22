def get_client_id(client_config):
    return f'{client_config.get("domain")}_{client_config.get("username")}_{client_config.get("org_id")}'
