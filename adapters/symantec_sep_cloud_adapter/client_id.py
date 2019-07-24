def get_client_id(client_config):
    return client_config['client_id'] + '_' + client_config['customer_id'] + '_' + client_config['domain_id']
