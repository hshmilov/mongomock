import hashlib


def get_client_id(client_config):
    if not client_config.get('company_name'):
        return client_config['domain'] + '_' + hashlib.md5(client_config['apikey'].encode('utf-8')).hexdigest()
    return client_config['domain'] + '_' + \
        hashlib.md5(client_config['apikey'].encode('utf-8')).hexdigest() + client_config['company_name']
