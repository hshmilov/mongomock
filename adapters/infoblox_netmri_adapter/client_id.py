def get_client_id(client_config):
    # AUTOADAPTER
    return f'{client_config["domain"]}_{client_config["username"]}'
