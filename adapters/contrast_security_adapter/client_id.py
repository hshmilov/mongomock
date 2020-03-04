import base64


def get_client_id(client_config):
    org_uuids_str = 'ALL'
    if client_config.get('org_uuids'):
        org_uuids_str = base64.b64encode(bytearray(','.join(client_config.get('org_uuids')), 'utf-8')).decode('utf-8')
    return f'{client_config["username"]}_{org_uuids_str}'
