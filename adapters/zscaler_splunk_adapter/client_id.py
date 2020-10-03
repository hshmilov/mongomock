def get_client_id(client_config):
    return f'{client_config.get("host")}_{client_config.get("username")}'
