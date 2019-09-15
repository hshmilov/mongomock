def get_client_id(client_config):
    return client_config.get('user_id') or (client_config.get('cidr') or '').split(',')[0] \
        or client_config.get('query_search') or 'api.shodan.com'
