def get_client_id(client_config):
    return f'{client_config.get("collection_name")}_{client_config.get("access_key")}'
