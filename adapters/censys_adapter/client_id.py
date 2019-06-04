import hashlib


def get_client_id(client_config):
    hash_id = hashlib.sha1(f'{client_config["api_id"]}_{client_config["search_query"]}'.encode('utf-8')).hexdigest()
    return hash_id
