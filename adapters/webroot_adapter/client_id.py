def get_client_id(client_config):
    return client_config['domain'] + '_' + client_config['gsm_key'] + '_' + client_config['site_id']
