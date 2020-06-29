from axonius.clients.wmi_query import consts


def get_client_id(client_config):
    return client_config[consts.HOSTNAMES]
