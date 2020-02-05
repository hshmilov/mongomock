import hashlib


def get_client_id(client_config):
    return client_config['domain'] + '_' + \
        hashlib.md5((client_config.get('apikey') or 'NONE').encode('utf-8')).hexdigest()
