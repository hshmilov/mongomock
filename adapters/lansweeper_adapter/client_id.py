from lansweeper_adapter import consts


def get_client_id(client_config):
    return client_config[consts.LANSWEEPER_HOST]
