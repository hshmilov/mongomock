import hashlib


def get_client_id(client_config):
    return hashlib.md5(client_config['apikey'].encode('utf-8')).hexdigest()
