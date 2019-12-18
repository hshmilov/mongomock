def get_client_id(client_config):
    domain = client_config['domain']
    dom_id = client_config['domain_id']
    ten_id = client_config['tenant_id']
    return f'{domain}:tenant-{ten_id}:domain-{dom_id}'
