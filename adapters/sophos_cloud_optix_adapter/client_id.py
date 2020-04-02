import hashlib


def get_client_id(client_config):
    hash_id = hashlib.sha1(client_config['apikey'].encode('utf-8')).hexdigest()
    return f'{client_config.get("domain")}_{hash_id}'
