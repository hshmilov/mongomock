from enum import Enum, auto

import getpass
import sys
import argparse

from axonius.clients.ldap.ldap_connection import LdapConnection

USAGE_EXAMPLE = 'ldap_connection_test.py -dc dc1.testdomain.test -d TestDomain -u Administrator --secure'


class SSLState(Enum):
    Unencrypted = auto()
    Verified = auto()
    Unverified = auto()


def parse_args():
    parser = argparse.ArgumentParser(epilog=USAGE_EXAMPLE)
    parser.add_argument('--dc-address', '-dc', type=str, help='DC Host')
    parser.add_argument('--domain', '-d', type=str, help='Domain')
    parser.add_argument('--username', '-u', type=str, help='Username')
    parser.add_argument('--password', '-p', type=str, help='Password')
    parser.add_argument('--secure', '-s', action='store_true', default=False, help='Use LDAPS')
    try:
        args = parser.parse_args()
    except Exception:
        print(parser.usage())
        return None
    return args


def main():
    args = parse_args()
    if not args:
        return -1

    if not args.dc_address or not args.username or not args.domain:
        print(f'Error: Address / Domain / Username are required')
        return -1

    password = args.password if args.password else getpass.getpass('Enter Password: ')
    username = f'{args.domain}\\{args.username}'

    if args.password:
        print(f'Connecting to {args.dc_address} with username {username} and password {args.password}')
    else:
        print(f'Connecting to {args.dc_address} with username {username}')

    ldap_connection = LdapConnection(
        args.dc_address,
        username,
        password,
        use_ssl=SSLState.Unverified if args.secure else SSLState.Unencrypted,
    )

    print(f'Connection Succeeded.')
    print(ldap_connection.root_dse)

    print(f'First Device: ')
    data = ldap_connection.get_extended_devices_list()
    for device in data['devices']:
        print(device)
        break

    return 0


if __name__ == '__main__':
    sys.exit(main())
