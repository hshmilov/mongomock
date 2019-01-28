from linux_ssh_adapter.consts import (DEFAULT_PORT, HOSTNAME, PORT)


def get_client_id(client_config):
    return client_config[HOSTNAME] + ':' + str(client_config.get(PORT, DEFAULT_PORT))
