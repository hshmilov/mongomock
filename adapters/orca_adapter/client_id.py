import hashlib


def get_client_id(client_config):
    api_declassified = hashlib.md5(client_config['apikey'].encode('utf-8')).hexdigest()
    return client_config['domain'] + '_' + api_declassified
