def get_client_id(client_config):
    return f'WORKDAY_SOAP_{client_config["domain"]}_{client_config["tenant"]}'
