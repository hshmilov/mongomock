from iboss_cloud_adapter.consts import DOMAIN_CONFIG


def get_client_id(client_config):
    return DOMAIN_CONFIG + '_' + client_config['username']
