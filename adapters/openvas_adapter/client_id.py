def get_client_id(client_config):
    domain = client_config.get('domain')
    protocol = client_config.get('gvm_protocol')
    username = client_config.get('username', 'NOUSER')
    # debug = 'DEBUG_' if client_config.get('_debug_file_assets') else ''
    # return f'OPENVAS_{debug}{protocol}://{domain}'
    return f'OPENVAS_{username}@{protocol}://{domain}'
