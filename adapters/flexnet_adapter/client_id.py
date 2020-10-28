import hashlib


def get_client_id(client_config):
    token_md5 = hashlib.md5(client_config.get('refresh_token').encode('utf-8')).hexdigest()
    return f'{client_config.get("domain")}_{client_config.get("organization_id")}_{token_md5}'
