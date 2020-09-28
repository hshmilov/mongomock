import hashlib


def get_client_id(client_config):
    token_md5 = hashlib.md5(client_config.get('apikey').encode('utf-8')).hexdigest()
    return token_md5
