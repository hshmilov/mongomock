import base64


def get_client_id(client_config):
    search_query_b64 = base64.b64encode(bytearray(client_config['search_query'], 'utf-8')).decode('utf-8')
    return f'{client_config["access_id"]}_{search_query_b64}'
