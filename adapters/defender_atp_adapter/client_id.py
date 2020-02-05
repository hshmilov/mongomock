def get_client_id(client_config):
    return client_config['tenant_id'] + '_' + client_config['client_id']
