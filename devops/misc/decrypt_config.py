#!/usr/bin/env python3
import argparse
import base64
from pprint import pprint

import paramiko
from pymongo import MongoClient
from pymongo.encryption import ClientEncryption
from axonius.consts.plugin_consts import KEYS_COLLECTION
from axonius.utils.encryption.mongo_encrypt import MongoEncrypt


DEFAULT_SSH_PATH = '/home/ubuntu/cortex/.axonius_settings/.db_key'
USAGE_EXAMPLE = 'decrypt_config.py -sp 20016 -dp 40016 -sP PASSWORD -p aws_adapter_0'


def parse_args():
    parser = argparse.ArgumentParser(epilog=USAGE_EXAMPLE)
    parser.add_argument('--db-host', '-dh', default='127.0.0.1', type=str, help='MongoDB Host')
    parser.add_argument('--db-port', '-dp', default=27017, type=int, help='MongoDB Port')
    parser.add_argument('--db-user', '-du', default='ax_user', type=str, help='MongoDB Username')
    parser.add_argument('--db-password', '-dP', default='ax_pass', type=str, help='MongoDB Password')
    parser.add_argument('--ssh-host', '-sh', default='127.0.0.1', type=str, help='SSH Host')
    parser.add_argument('--ssh-port', '-sp', default=22, type=int, help='SSH Port')
    parser.add_argument('--ssh-user', '-su', default='ubuntu', type=str, help='SSH Username')
    parser.add_argument('--ssh-password', '-sP', type=str, help='SSH Password')
    parser.add_argument('--ssh-path', '-spath', default=DEFAULT_SSH_PATH, type=str, help='SSH Database key path')
    parser.add_argument('--key', '-k', type=str, help='Base64 encoded database key')
    parser.add_argument('--action', '-a', type=str, help='Action name to decrypt its config')
    parser.add_argument('--plugin', '-p', type=str, help='plugin_unique_name to decrypt its config')
    try:
        args = parser.parse_args()
    except Exception:
        print(parser.usage())
        return None
    return args


def get_db_pass_from_ssh(host: str, port: int, username: str, password: str, path: str) -> str:
    """
    Get database encryption password from remote host via ssh connection
    :param host: host address
    :param port: host ssh port
    :param username: host ssh username
    :param password: host ssh password
    :param path: db encryption key path on host
    :return: base64 encoded encryption key
    """
    try:
        print(f'Getting db pass from {host}:{port}')
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=username, password=password, port=port)
        (stdin, stdout, stderr) = client.exec_command(f'cat {path}')
        db_pass = stdout.readline()
        client.close()
        return db_pass
    except Exception as e:
        print(f'Error getting db pass from {host}:{port} : {e}')


def decrypt_action_data(mongo_client: MongoClient, mongo_enc: ClientEncryption, action_name: str) -> None:
    """
    Decrypt and print action client_data
    :param mongo_client: mongo client object
    :param mongo_enc: database encryption object
    :param action_name: action name for decryption
    :return: None
    """
    action_data = mongo_client['reports']['saved_actions'].find_one({
        'name': action_name
    })
    if not action_data:
        print(f'action "{action_name}" was not found')
        return

    config = action_data.get('action', {}).get('config')
    if config:
        for key, val in config.items():
            if val:
                config[key] = db_decrypt(mongo_enc, val)
        print(f'{action_name}:')
        pprint(config)


def decrypt_adapter_data(mongo_client: MongoClient, mongo_enc: ClientEncryption, plugin_unique_name: str) -> None:
    """
    Decrypt and print adapter client_data
    :param mongo_client: mongo client object
    :param mongo_enc: database encryption object
    :param plugin_unique_name: plugin unique name for decryption
    :return: None
    """
    db_cursor = mongo_client[plugin_unique_name]['clients'].find({})
    for client in db_cursor:
        client_name = client.get('client_id')
        try:
            client_config = client.get('client_config')
            if client_config:
                for key, val in client_config.items():
                    if val:
                        client_config[key] = db_decrypt(mongo_enc, val)
                print(f'{client_name}:')
                pprint(client_config)
            else:
                print(f'No client config for {plugin_unique_name}')
        except Exception as e:
            print(f'Error decrypting {client_name}: {e}')


def main():
    args = parse_args()
    db_key = None
    if not args.plugin and not args.action:
        print('Please provide --action or --plugin')
        return

    if args.key:
        db_key = args.key
    elif args.ssh_host:
        db_key = get_db_pass_from_ssh(args.ssh_host,
                                      args.ssh_port,
                                      args.ssh_user,
                                      args.ssh_password,
                                      args.ssh_path)
    if not db_key:
        print('Error: No database key')
        return
    db_key = base64.b64decode(db_key)

    # Connect to mongodb.
    mongo_client = MongoClient(args.db_host, username=args.db_user, password=args.db_password, port=args.db_port)
    enc = MongoEncrypt.get_db_encryption(mongo_client, KEYS_COLLECTION, db_key)

    # Decrypt clients data
    if args.action:
        decrypt_action_data(mongo_client, enc, args.action)
    if args.plugin:
        decrypt_adapter_data(mongo_client, enc, args.plugin)


if __name__ == '__main__':
    main()
