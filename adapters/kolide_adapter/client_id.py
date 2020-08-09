import hashlib


def get_client_id(client_config):
    apikey = hashlib.md5(f'axonius_{client_config.get("apikey")}'.encode('utf-8')).hexdigest()
    return f'{client_config.get("domain")}_{apikey}'
