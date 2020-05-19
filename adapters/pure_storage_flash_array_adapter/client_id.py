import hashlib


def get_client_id(client_config):
    private_key_md5 = hashlib.md5(client_config['private_key'].encode('utf-8')).hexdigest()

    return client_config['domain'] + '_' + client_config['application_id'] + '_' + private_key_md5
