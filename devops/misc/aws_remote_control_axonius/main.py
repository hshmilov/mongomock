import sys
import os
import json
from collections import OrderedDict
from typing import List

import boto3
import colorama
import requests
import terminaltables


SECRETS_PATH = os.path.join('secrets', 'secrets.json')
ROLES_PATH = os.path.join('secrets', 'roles.json')
API_PATH = os.path.join('secrets', 'api.json')
DEFAULT_REGION = 'us-east-2'


def print_logo():
    print_green('''
          __   __  ____   _   _  _____  _    _   _____
    /\    \ \ / / / __ \ | \ | ||_   _|| |  | | / ____|
   /  \    \ V / | |  | ||  \| |  | |  | |  | || (___  
  / /\ \    > <  | |  | || . \ |  | |  | |  | | \___ \  
 / ____ \  / . \ | |__| || |\  | _| |_ | |__| | ____) |
/_/    \_\/_/ \_\\ \____/ |_| \_||_____| \____/ |_____/
 
              Axonius Instance Manager 1.0
    ''')


def print_green(msg):
    print(f'{colorama.Fore.GREEN}{msg}{colorama.Style.RESET_ALL}')


def print_blue(msg):
    print(f'{colorama.Fore.LIGHTBLUE_EX}{msg}{colorama.Style.RESET_ALL}')


def print_red(msg):
    print(f'{colorama.Fore.RED}{msg}{colorama.Style.RESET_ALL}')


def aws_describe(clients: dict):
    for client_name, client in clients.items():
        all_instances = client.describe_instances(Filters=[{'Name': 'tag-key', 'Values': ['axonius-esentire']}])
        for reservation in all_instances['Reservations']:
            for instance in reservation['Instances']:
                yield client_name, client, instance


def aws_start(instances, instance_id: str):
    print(f'Locating {instance_id}...')
    for client_name, client, instance_raw in instances:
        if instance_raw['InstanceId'] == instance_id:
            client.start_instances(InstanceIds=[instance_id])
            print_green(f'Successfully started {instance_id} in account {client_name}')
            break
    else:
        print_red(f'Could not find instance-id {instance_id}')


def aws_stop(instances, instance_id: str):
    print(f'Locating {instance_id}...')
    for client_name, client, instance_raw in instances:
        if instance_raw['InstanceId'] == instance_id:
            client.stop_instances(InstanceIds=[instance_id])
            print_green(f'Successfully stopped {instance_id} in account {client_name}')
            break
    else:
        print_red(f'Could not find instance-id {instance_id}')


def show_describe(instances: list):
    table_data = [
        ['Account', 'Instance ID', 'Domain', 'Public IP', 'State']
    ]

    print('Axonius Instances:')
    for client_name, client, instance in instances:
        domain = ''
        for tag_raw in instance['Tags']:
            if tag_raw['Key'] == 'domain':
                domain = tag_raw['Value']
        state = (instance.get('State') or {}).get('Name')
        table_data.append(
            [client_name, instance['InstanceId'], domain, instance['PublicIpAddress'], state]
        )

    table = terminaltables.AsciiTable(table_data)
    print(table.table)


def prepare_boto(secrets: dict, roles: List[dict]):
    all_clients = OrderedDict()
    all_clients['primary'] = boto3.client('ec2', **secrets, region_name=DEFAULT_REGION)

    sts_client = boto3.client('sts', **secrets, region_name=DEFAULT_REGION)
    print_green(f'Successfully created primary aws client')
    for role_dict in roles:
        creds = sts_client.assume_role(RoleArn=role_dict['arn'], RoleSessionName='Axonius')
        all_clients[role_dict['name']] = boto3.client('ec2',
                                                      aws_access_key_id=creds['Credentials']['AccessKeyId'],
                                                      aws_secret_access_key=creds['Credentials']['SecretAccessKey'],
                                                      aws_session_token=creds['Credentials']['SessionToken'],
                                                      region_name=DEFAULT_REGION
                                                      )
        print_green(f'Successfully assumed role {role_dict["arn"]} for account {role_dict["name"]}')

    return all_clients


def show_help():
    print('''Usage:
    {name} describe - show all instances
    {name} stop [instance-id]
    {name} start [instance-id]
    {name} cycle [domain]
'''.strip().format(name=sys.argv[0]))


def start_discovery_cycle(domain, username, password):
    resp = requests.post(f'https://{domain}/api/login',
                         json={'user_name': username, 'password': password, 'remember_me': False}
                         )
    resp.raise_for_status()
    headers = None
    for header in resp.headers['Set-Cookie'].split(','):
        if header.strip().startswith('session'):
            headers = {'cookie': header.split(';')[0].strip()}
            break
    else:
        print_red(f'Incorrect credentials')
        return -1

    resp = requests.post(f'https://{domain}/api/research_phase', headers=headers)
    resp.raise_for_status()
    print_green(f'Successfully started discovery cycle in {domain}')


def main():
    if not os.path.exists(SECRETS_PATH):
        print(f'Error: secrets file not found. Please set {SECRETS_PATH}')
        return -1

    if not os.path.exists(ROLES_PATH):
        print(f'Error: roles file not found. Please set {ROLES_PATH}')
        return -1

    with open(ROLES_PATH, 'rt') as f:
        roles = json.loads(f.read())

    with open(SECRETS_PATH, 'rt') as f:
        secrets = json.loads(f.read())

    command = sys.argv[1] if len(sys.argv) > 1 else None
    args = sys.argv[2:]

    colorama.init()
    print_logo()
    print('Initializing..')
    try:
        clients = prepare_boto(secrets, roles)
    except Exception as e:
        print_red(f'There was a table initializing aws: {str(e)}')
        return -1

    instances = list(aws_describe(clients))
    show_describe(instances)

    if command == 'start':
        aws_start(instances, args[0])
    elif command == 'stop':
        aws_stop(instances, args[0])
    elif command == 'cycle':
        domain = args[0]
        with open(API_PATH, 'rt') as f:
            api_creds = json.loads(f.read())

        user_name = None,
        for api_raw in api_creds:
            if api_raw['domain'].lower() == domain.lower():
                start_discovery_cycle(domain, api_raw['user_name'], api_raw['password'])
                break
        else:
            print_red(f'Could not find credentials for domain {domain}')
            return -1
    elif command == 'describe':
        pass
    else:
        show_help()

    return 0


if __name__ == '__main__':
    sys.exit(main())
