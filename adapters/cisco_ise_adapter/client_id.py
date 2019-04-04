from cisco_ise_adapter.consts import CLIENT_CONFIG_FIELDS


def get_client_id(client_config):
    return client_config[CLIENT_CONFIG_FIELDS.domain]
