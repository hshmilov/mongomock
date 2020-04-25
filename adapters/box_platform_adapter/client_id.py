def get_client_id(client_config):
    return f'BOX_PLATFORM_{client_config["domain"]}_{client_config["client_id"]}'
