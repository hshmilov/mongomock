import hashlib


def get_client_id(client_config):
    api_key_md5 = hashlib.md5(client_config['apikey'].encode('utf-8')).hexdigest()
    return f'{client_config["domain"]}_{api_key_md5}'
