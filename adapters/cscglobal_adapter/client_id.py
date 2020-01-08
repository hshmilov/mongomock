def get_client_id(client_config):
    return f'CSCGlobal_Domain:{client_config.get("domain")}_Zone:{client_config.get("zone_name")}'
