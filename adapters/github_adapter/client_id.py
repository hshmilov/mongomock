import hashlib


def get_client_id(client_config):
    api_key_hash = hashlib.md5(client_config['auth_token'].encode('utf-8')).hexdigest()
    org = client_config['org']
    domain = client_config['domain']
    return f'{domain}_{org}_{api_key_hash}'
