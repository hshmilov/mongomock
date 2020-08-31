import hashlib


def get_client_id(client_config):
    token_key_md5 = hashlib.md5(client_config['token'].encode('utf-8')).hexdigest()
    return f'{client_config["domain"]}_{token_key_md5}'
