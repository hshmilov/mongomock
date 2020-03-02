import hashlib


def get_client_id(client_config):
    api_key_md5 = hashlib.md5(client_config['api_key'].encode('utf-8')).hexdigest()

    return f'{api_key_md5}'
