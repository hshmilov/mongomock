def get_client_id(client_config):
    return f'{client_config.get("server")}_{client_config.get("username")}'
