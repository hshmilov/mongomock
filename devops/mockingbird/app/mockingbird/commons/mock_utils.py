import importlib
import random
import string   # pylint: disable=deprecated-module
import struct
import socket

from typing import List
from datetime import datetime, timedelta

from axonius.devices.device_adapter import DeviceAdapter
from axonius.users.user_adapter import UserAdapter
from axonius.utils.datetime import parse_date
from mockingbird.commons.mock_network_entity import MockNetworkEntity, MockNetworkEntityProperties
from mockingbird.commons import consts


def ip2int(addr):
    return struct.unpack('!I', socket.inet_aton(addr))[0]


def int2ip(addr):
    return str(socket.inet_ntoa(struct.pack('!I', addr)))


def create_my_device_adapter(adapter_name: str) -> DeviceAdapter:
    module = importlib.import_module(f'{adapter_name}_adapter.service')
    adapter_class = getattr(module, ''.join(
        [word.capitalize() for word in adapter_name.replace('_', ' ').replace('-', ' ').split(' ')]) + 'Adapter')
    return adapter_class.MyDeviceAdapter(set(), set())


def create_my_user_adapter(adapter_name: str) -> UserAdapter:
    module = importlib.import_module(f'{adapter_name}_adapter.service')
    adapter_class = getattr(module, ''.join(
        [word.capitalize() for word in adapter_name.replace('_', ' ').replace('-', ' ').split(' ')]) + 'Adapter')
    return adapter_class.MyUserAdapter(set(), set())


def create_generic_device_adapter() -> DeviceAdapter:
    return DeviceAdapter(set(), set())


def recursive_remove_none(obj):
    if isinstance(obj, list):
        return [x for x in obj if x is not None]

    if isinstance(obj, dict):
        return {k: recursive_remove_none(v) for k, v in obj.items() if v is not None}

    return obj


def get_all_ips(device: DeviceAdapter) -> List[str]:
    if not device.network_interfaces:
        return []

    ips = []
    for nic in device.network_interfaces:
        try:
            if nic.ips:
                ips.extend(nic.ips)
        except Exception:
            # This is legitimate. Sometimes, a NIC simply doesn't have ips.
            pass

    return ips


def get_all_macs(device: DeviceAdapter) -> List[str]:
    if not device.network_interfaces:
        return []

    macs = []
    for nic in device.network_interfaces:
        try:
            if nic.mac:
                macs.append(nic.mac)
        except Exception:
            # This is legitimate. Sometimes, a NIC simply doesn't have macs.
            pass

    return macs


def get_random_windows_pc_name(username=None) -> str:
    prefix = random.choice(['PC-', 'DESKTOP-', 'Windows-', 'Win-'])

    suffix = None
    if username:
        rand_user_manipulation = random.randint(1, 5)
        if rand_user_manipulation == 1:
            suffix = username.replace(' ', '-')
        if rand_user_manipulation == 2:
            suffix = username.replace(' ', '')
        if rand_user_manipulation == 3:
            suffix = username.split(' ')[0] + username.split(' ')[1][0]
        if rand_user_manipulation == 4:
            suffix = username.split(' ')[1] + username.split(' ')[0][0]
        if rand_user_manipulation == 5:
            suffix = username.split(' ')[0] + ''.join(random.choices(string.digits, k=4))

        post_manipulation = random.randint(1, 5) == 1
        if post_manipulation == 1:
            suffix = suffix.lower()
        if post_manipulation == 2:
            suffix = suffix.upper()
    else:
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))

    return prefix + suffix


def get_random_manager_name() -> str:
    return random.choice([
        'Ryan Duffy',
        'Donald Deshong',
        'Joel Turner',
        'Carl Pein',
        'Danielle Lance',
        'Brandy Bumgarner',
        'Floyd Brady',
        'Mary Signs',
        'William Saari',
        'Charles Woods'
    ])


def get_random_windows_host_os() -> str:
    return random.choice(
        [
            'Windows 10 Pro', 'Windows 10 Home', 'Windows 10 Enterprise',
            'Windows 8.1 Pro', 'Windows 8.1 Enterprise',
            'Windows 8',
            'Windows 7 Enterprise', 'Windows 7 Ultimate',
            'Windows Vista Business', 'Windows Vista Enterprise',
            'Windows XP SP2'
        ]
    )


def get_random_linux_os_host() -> str:
    return random.choice(
        [
            'Ubuntu 16.04 LTS', 'Ubuntu 14.04 LTS', 'Ubuntu 18.04 LTS',
            'Centos 6', 'Centos 7',
        ]
    )


def get_random_software_list() -> List[dict]:
    return [
        {
            'vendor': 'Microsoft Corporation',
            'name': 'Microsoft Office Professional Plus 2016 - en-us',
            'version': '16.0.11029.20108'
        },
        {
            'vendor': 'Microsoft Corporation',
            'name': 'Microsoft Visual C++ 2008 Redistributable - x64 9.0.30729.6161',
            'version': '9.0.30729.6161'
        },
        {
            'vendor': 'Adobe Systems Incorporated',
            'name': 'Adobe Acrobat Reader DC',
            'version': '19.010.20069'
        },
    ]


def get_random_software_vulnerable_list() -> List[dict]:
    return [
        {
            'vendor': 'Adobe Systems Incorporated',
            'name': 'Adobe Flash Player 30 PPAPI',
            'version': '30.0.0.113'
        },
    ]


def get_random_hardware_list() -> List[dict]:
    return consts.CONNECTED_HARDWARE


def get_random_shares_list() -> List[dict]:
    return consts.SHARES


def get_random_services_list() -> List[dict]:
    return [{'name': line} for line in consts.SERVICES]


def get_random_processes_list() -> List[dict]:
    return [{'name': line} for line in consts.PROCESSES]


def get_random_linux_software_list() -> List[dict]:
    return [
        {
            'name': 'acl',
            'version': '2.2.52-3'
        },
        {
            'name': 'apparmor',
            'version': '2.10.95'
        },
        {
            'name': 'bzip2',
            'version': '1.0.6-8'
        },
        {
            'name': 'ftp',
            'version': '0.17-33'
        },
        {
            'name': 'git',
            'version': '1:2.7.4'
        },
        {
            'name': 'gzip',
            'version': '1.6-4'
        },
        {
            'name': 'iso-codes',
            'version': '3.65-1'
        },
        {
            'name': 'libc6',
            'version': '2.23'
        },
        {
            'name': 'libpython2.7',
            'version': '2.7.12-1'
        },
        {
            'name': 'libpython-stdlib',
            'version': '2.7.12-1~16.04'
        },
    ]


def get_random_windows_available_security_patches() -> List[dict]:
    return [
        {
            'title': 'Definition Update for Windows Defender Antivirus - KB2267602 (Definition 1.285.492.0)',
            'kb_article_ids': ['2267602'],
            'patch_type': 'Software',
            'categories': ['Definition Updates', 'Windows Defender'],
            'publish_date': parse_date('2019-01-30 02:00:00')
        },
        {
            'title': 'Windows Malicious Software Removal Tool x64 - January 2019 (KB890830)',
            'kb_article_ids': ['890830'],
            'patch_type': 'Software',
            'categories': ['Update Rollups'],
            'publish_date': parse_date('2019-01-08 02:00:00')
        }
    ]


def random_day_generator(max_days_ago, min_days_ago):
    return datetime.now() - timedelta(
        days=random.randint(min_days_ago, max_days_ago),
        seconds=random.randint(0, 59),
        minutes=random.randint(0, 59),
        hours=random.randint(0, 18)
    )


def last_seen_generator(
        entity: MockNetworkEntity, entity_property: MockNetworkEntityProperties, max_days_ago, min_days_ago
):
    if not min_days_ago:
        min_days_ago = 0
    assert max_days_ago > min_days_ago
    last_seen = random_day_generator(max_days_ago, min_days_ago)

    if not entity.get_specific(entity_property):
        entity.add_specific(entity_property, entity.__class__(set(), set()))

    entity.get_specific(entity_property).last_seen = last_seen
