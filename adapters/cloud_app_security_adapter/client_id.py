import hashlib


def get_client_id(client_config):
    token_md5 = hashlib.md5(client_config.get('token').encode('utf-8')).hexdigest()
    return f'{client_config.get("domain")}_{token_md5}'
