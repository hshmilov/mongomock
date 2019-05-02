#!/usr/local/bin/python3

from pprint import pprint

from axoniussdk.argument_parser import ArgumentParser
from axoniussdk.client import RESTClient

LINUX_SSH_ADAPTER_NAME = 'linux_ssh_adapter'

CLIENT_CONFIG = {
    'host_name': 'example',
    'user_name': 'example_user',
    'password': 'example_password',
    'is_sudoer': False,
}


def get_linux_ssh_instances(client):
    ret, resp = client.get_adapters()
    assert ret == 200
    return [instance['node_id'] for instance in resp[LINUX_SSH_ADAPTER_NAME]]


def get_linux_ssh_schema(client):
    ret, resp = client.get_adapters()
    assert ret == 200
    return resp[LINUX_SSH_ADAPTER_NAME][0]['schema']


def add_ssh_client(rest_client, client_config, instance_id):
    schema = get_linux_ssh_schema(rest_client)
    required = schema['required']
    schema_names = [field['name'] for field in schema['items']]

    for required_item in required:
        if required_item not in client_config:
            raise RuntimeError(f'Missing required item {required_item}')

    for item in client_config:
        if item not in schema_names:
            raise RuntimeError(f'Invalid item {item}')

    rest_client.add_client(LINUX_SSH_ADAPTER_NAME,
                           client_config,
                           instance_id)


def main():
    args = ArgumentParser().parse_args()
    client = RESTClient(args.axonius_url,
                        auth=args.auth,
                        headers=args.headers,
                        verify=not args.no_verify_ssl)

    print('Nodes: ')
    pprint(get_linux_ssh_instances(client))

    print('Schema: ')
    pprint(get_linux_ssh_schema(client))

    first_instance_id = get_linux_ssh_instances(client)[0]

    print(f'Adding client for node {first_instance_id}')
    add_ssh_client(client, CLIENT_CONFIG, first_instance_id)


if __name__ == '__main__':
    main()
