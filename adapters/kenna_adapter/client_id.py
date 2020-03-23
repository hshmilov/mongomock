import hashlib


def get_client_id(client_config):
    hash_id = hashlib.sha1(client_config['api_token'].encode('utf-8')).hexdigest()
    return f'{client_config["domain"]}_{hash_id}'
