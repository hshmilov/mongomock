from axonius.clients.beyond_trust.consts import BEYOND_TRUST_HOST, BEYOND_TRUST_DATABASE


def get_client_id(client_config):
    return client_config.get(BEYOND_TRUST_HOST) + '_' + client_config.get(BEYOND_TRUST_DATABASE)
