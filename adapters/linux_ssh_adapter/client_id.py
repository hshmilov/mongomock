from axonius.clients.linux_ssh.consts import (DEFAULT_PORT, HOSTNAME, PORT, COMMAND_NAME)


def get_client_id(client_config):
    args = [client_config[HOSTNAME],
            str(client_config.get(PORT) or DEFAULT_PORT)]
    if client_config.get(COMMAND_NAME):
        args.append(client_config[COMMAND_NAME].lower().strip().replace(' ', '_').replace('-', '_'))
    return ':'.join(args)
