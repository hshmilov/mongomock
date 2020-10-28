from axonius.clients.oracle_cloud import consts


def get_client_id(client_config):
    return client_config[consts.ORACLE_CLOUD_USER] + '_' + client_config[consts.ORACLE_TENANCY] \
        + '_' + client_config[consts.ORACLE_REGION]
