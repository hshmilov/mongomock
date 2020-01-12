import hashlib


def get_client_id(client_config):
    api_key_md5 = hashlib.md5(client_config['api_key'].encode('utf-8')).hexdigest()
    division_ids_str = '+'.join(client_config.get('division_ids')) \
        if client_config.get('division_ids') else 'ALL'
    return f'digicert_{client_config["account_id"]}_{division_ids_str}_{api_key_md5}'
