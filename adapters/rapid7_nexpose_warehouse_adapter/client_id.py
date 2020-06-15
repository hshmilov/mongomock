def get_client_id(client_config):
    return f'{client_config["server"]}_{client_config["database"]}_{client_config["username"]}'
