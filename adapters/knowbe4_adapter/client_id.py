import hashlib


def get_client_id(client_config):
    return client_config['domain'] + '_' + hashlib.md5(client_config['apikey'].encode('utf-8')).hexdigest()
