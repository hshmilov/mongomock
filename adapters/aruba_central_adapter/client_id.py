def get_client_id(client_config):
    return f'{client_config.get("domain")}_{client_config.get("customer_id")}_' \
           f'{client_config.get("client_id")}_{client_config.get("username")}'
