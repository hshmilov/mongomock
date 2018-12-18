from linux_ssh_adapter.consts import HOSTNAME, PORT, DEFAULT_PORT


def get_client_id(client_config):
    if PORT not in client_config:
        client_config[PORT] = DEFAULT_PORT
    return client_config[HOSTNAME] + ':' + str(client_config[PORT])
