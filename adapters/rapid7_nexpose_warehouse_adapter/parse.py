import logging
from collections import defaultdict
from typing import Tuple

from axonius.clients.postgres.connection import PostgresConnection
from rapid7_nexpose_warehouse_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


def _get_vulnerabilities_by_asset_id(connection) -> Tuple[dict, dict]:
    try:
        vulnerabilities_counter = 0
        vulnerabilities = {}
        asset_vulnerabilities = defaultdict(list)

        # Dict of vulnerabilities, keys are by vulnerability_id
        for vulnerability in connection.query(consts.VULNERABILITIES_QUERY):
            if isinstance(vulnerability, dict) and vulnerability.get('vulnerability_id'):
                vulnerabilities[vulnerability.get('vulnerability_id')] = vulnerability

        for asset_vulnerability in connection.query(consts.ASSET_VULNERABILITIES_QUERY):
            if not isinstance(asset_vulnerability, dict):
                continue

            vulnerability_id = asset_vulnerability.get('vulnerability_id')
            asset_id = asset_vulnerability.get('asset_id')

            if not vulnerability_id or not asset_id:
                continue

            asset_vulnerabilities[asset_id].append(vulnerability_id)

        logger.debug(
            f'Fetching from vulnerabilities table completed successfully, total of {vulnerabilities_counter}')
        return asset_vulnerabilities, vulnerabilities
    except Exception:
        logger.warning(f'Failed getting vulnerabilities', exc_info=True)
        return {}, {}


def _get_tags(connection):
    try:
        tags_counter = 0
        tags = {}
        asset_tags = defaultdict(list)

        # Dict of tags, keys are by tag_id
        for tag in connection.query(consts.TAGS_QUERY):
            if isinstance(tag, dict) and tag.get('tag_id'):
                tags[tag.get('tag_id')] = tag

        for asset_tag in connection.query(consts.ASSET_TAGS_QUERY):
            if isinstance(asset_tag, dict) and asset_tag.get('tag_id') and asset_tag.get('asset_id'):
                if tags.get(asset_tag.get('tag_id')):
                    tags_counter += 1
                    asset_tags[asset_tag.get('asset_id')].append(tags.get(asset_tag.get('tag_id')))

        logger.debug(f'Fetching from tags table completed successfully, total of {tags_counter}')
        return asset_tags
    except Exception:
        logger.warning(f'Failed getting tags', exc_info=True)
        return {}


def _get_users(connection):
    try:
        users_counter = 0
        users = defaultdict(list)
        for user in connection.query(consts.USERS_QUERY):
            if isinstance(user, dict) and user.get('asset_id'):
                users_counter += 1
                users[user.get('asset_id')].append(user)

        logger.debug(f'Fetching from users table completed successfully, total of {users_counter}')
        return users
    except Exception:
        logger.warning(f'Failed getting users', exc_info=True)
        return {}


def _get_groups(connection):
    try:
        groups_counter = 0
        groups = defaultdict(list)
        for group in connection.query(consts.GROUPS_QUERY):
            if isinstance(group, dict) and group.get('asset_id'):
                groups_counter += 1
                groups[group.get('asset_id')].append(group)

        logger.debug(f'Fetching from groups table completed successfully, total of {groups_counter}')
        return groups
    except Exception:
        logger.warning(f'Failed getting groups', exc_info=True)
        return {}


def _get_ports(connection):
    try:
        services_counter = 0
        services = defaultdict(list)
        for service in connection.query(consts.SERVICES_QUERY):
            if isinstance(service, dict) and service.get('asset_id'):
                services_counter += 1
                services[service.get('asset_id')].append(service)

        logger.debug(f'Fetching from services table completed successfully, total of {services_counter}')
        return services
    except Exception:
        logger.warning(f'Failed getting assets', exc_info=True)
        return {}


def _get_installed_software(connection):
    try:
        softwares_counter = 0
        softwares = defaultdict(list)
        for software in connection.query(consts.INSTALLED_SOFTWARE_QUERY):
            if isinstance(software, dict) and software.get('asset_id'):
                softwares_counter += 1
                softwares[software.get('asset_id')].append(software)

        logger.debug(f'Fetching from softwares table completed successfully, total of {softwares_counter}')
        return softwares
    except Exception as e:
        logger.warning(f'Failed getting softwares. {str(e)}', exc_info=True)
        return {}


def _get_policies(connection):
    try:
        policies_counter = 0
        policies = {}
        asset_policies = defaultdict(list)

        # Dict of vulnerabilities, keys are by vulnerability_id
        for policy in connection.query(consts.POLICIES_QUERY):
            if isinstance(policy, dict) and policy.get('policy_id'):
                policies[policy.get('policy_id')] = policy

        for asset_policy in connection.query(consts.ASSET_POLICIES_QUERY):
            if (isinstance(asset_policy, dict) and
                    asset_policy.get('policy_id') and
                    asset_policy.get('asset_id')):
                if policies.get(asset_policy.get('policy_id')):
                    policies_counter += 1
                    asset_policies[asset_policy.get('asset_id')].append(policies.get(asset_policy.get('policy_id')))

        logger.debug(f'Fetching from policies table completed successfully, total of {policies_counter}')
        return asset_policies
    except Exception:
        logger.warning(f'Failed getting policies', exc_info=True)
        return {}


def _get_devices(connection):
    try:
        asset_counter = 0
        devices = defaultdict(list)
        for device in connection.query(consts.ASSET_QUERY):
            if isinstance(device, dict) and device.get('asset_id'):
                asset_counter += 1
                devices[device.get('asset_id')].append(device)

        logger.debug(f'Fetching from assets table completed successfully, total of {asset_counter}')
        return devices
    except Exception:
        logger.warning(f'Failed getting assets', exc_info=True)
        return {}


def _get_devices_info(client_data):
    try:
        devices_info = {
            'vulnerabilities': _get_vulnerabilities_by_asset_id(client_data),
            'users': _get_users(client_data),
            'groups': _get_groups(client_data),
            'tags': _get_tags(client_data),
            'ports': _get_ports(client_data),
            'installed_softwares': _get_installed_software(client_data),
            'policies': _get_policies(client_data)
        }

        logger.debug(f'Finished collecting and combining devices information')
        return devices_info
    except Exception:
        logger.warning('Failed getting device info', exc_info=True)
        return {}


# pylint: disable=too-many-nested-blocks
def _build_device_info(devices_info: dict, device: dict, asset_id: str):
    try:
        try:
            device['extra_vulnerabilities'] = []
            if isinstance(devices_info.get('vulnerabilities'), tuple):
                asset_vulnerabilities, vulnerabilities = devices_info.get('vulnerabilities')
                if isinstance(asset_vulnerabilities, dict) and isinstance(vulnerabilities, dict):
                    for vuln_id in (asset_vulnerabilities.get(asset_id) or []):
                        vuln_data = vulnerabilities.get(vuln_id)
                        if vuln_data and isinstance(vuln_data, dict):
                            device['extra_vulnerabilities'].append(vuln_data)
        except Exception:
            logger.exception(f'Problem parsing vulnerabilities')

        if isinstance(devices_info.get('users'), dict) and devices_info.get('users'):
            device['extra_users'] = devices_info.get('users').get(asset_id) or []

        if isinstance(devices_info.get('groups'), dict) and devices_info.get('groups'):
            device['extra_groups'] = devices_info.get('groups').get(asset_id) or []

        if isinstance(devices_info.get('tags'), dict) and devices_info.get('tags'):
            device['extra_tags'] = devices_info.get('tags').get(asset_id) or []

        if isinstance(devices_info.get('ports'), dict) and devices_info.get('ports'):
            device['extra_ports'] = devices_info.get('ports').get(asset_id) or []

        installed_softwares = devices_info.get('installed_softwares')
        if isinstance(installed_softwares, dict) and installed_softwares:
            device['extra_installed_softwares'] = devices_info.get('installed_softwares').get(asset_id) or []

        if isinstance(devices_info.get('policies'), dict) and devices_info.get('policies'):
            device['extra_policies'] = devices_info.get('policies').get(asset_id) or []

        return device
    except Exception:
        logger.exception('Failed building device info')


def get_rapid7_warehouse_connection(client_config):
    connection = PostgresConnection(
        host=client_config['server'],
        port=int(client_config.get('port')),
        username=client_config['username'],
        password=client_config['password'],
        db_name=client_config.get('database'))

    connection.set_credentials(username=client_config['username'],
                               password=client_config['password'])
    with connection:
        connection.set_devices_paging(consts.DEVICE_PAGINATION)
        for _ in connection.query(consts.ASSET_QUERY):
            break
    return connection


def _query_devices_by_client_rapid7_warehouse(client_config):
    client_data = get_rapid7_warehouse_connection(client_config)
    with client_data:
        client_data.set_devices_paging(consts.DEVICE_PAGINATION)
        devices_info = _get_devices_info(client_data)
        logger.debug(f'Start querying dim_asset')
        all_assets = list(client_data.query(consts.ASSET_QUERY))
        logger.info(f'Finished fetching from db')
        for device in all_assets:
            if isinstance(device, dict) and client_config['drop_only_ip_devices']:
                if not device.get('mac_address') and not device.get('host_name'):
                    continue

            if isinstance(device, dict) and device.get('asset_id'):
                device_to_yield = device.copy()
                _build_device_info(devices_info, device_to_yield, device_to_yield.get('asset_id'))
                yield device_to_yield
