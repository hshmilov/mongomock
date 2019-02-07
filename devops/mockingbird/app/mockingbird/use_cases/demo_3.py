import random

import uuid
from datetime import datetime, timedelta

from aws_adapter.service import AWSIPRule
from mockingbird.commons import mock_utils
from mockingbird.commons.mock_network import MockNetwork
from mockingbird.commons.mock_network_device import MockNetworkDevice, MockNetworkDeviceProperties
from mockingbird.commons.mock_network_user import MockNetworkUserProperties, MockNetworkUser
from mockingbird.mock_adapters.aws import AwsAdapterParser
from mockingbird.mock_adapters.carbon_black_response import CarbonBlackResponseAdapterParser
from mockingbird.mock_adapters.splunk import SplunkAdapterParser
from mockingbird.mock_manager import MockManager
from mockingbird.mock_adapters.ad import AdAdapterParser
from mockingbird.mock_adapters.chef import ChefAdapterParser


DOMAIN = 'rsac.com'
EMPLOYEE_ID_START = 880000
COMPANY_SITE_LOCATIONS = ['Columbus', 'Richmond', 'New York', 'Boston']
WINDOWS_DEVICES_IN_NETWORK = 11849  # Number of devices in network
LINUX_DEVICES_IN_NETWORK = 7412
USERS_IN_NETWORK = round(WINDOWS_DEVICES_IN_NETWORK * 1.1)

USER_EXISTENCE_STATS = {
    'items-type': 'standalone',
    'items': [
        {
            'stats': {
                'value': MockNetworkUserProperties.ADUser
            },
            'percentage': 1
        }
    ]
}

LAST_SEEN_STATS = {
    MockNetworkDeviceProperties.ADDevice: [
        {
            'percentage': 0.9,
            'function': mock_utils.last_seen_generator,
            'args': (7, 0)
        },
        {
            'percentage': 0.1,
            'function': mock_utils.last_seen_generator,
            'args': (365, 300)
        }
    ],
    MockNetworkDeviceProperties.EpoDevice: [
        {
            'percentage': 0.98,
            'function': mock_utils.last_seen_generator,
            'args': (6, 0)
        },
        {
            'percentage': 0.02,
            'function': mock_utils.last_seen_generator,
            'args': (365, 7)
        }
    ],
    MockNetworkDeviceProperties.CarbonBlackResponseDevice: [
        {
            'percentage': 0.94,
            'function': mock_utils.last_seen_generator,
            'args': (7, 0)
        },
        {
            'percentage': 0.06,
            'function': mock_utils.last_seen_generator,
            'args': (365, 300)
        }
    ],
    MockNetworkDeviceProperties.ChefDevice: [
        {
            'percentage': 0.92,
            'function': mock_utils.last_seen_generator,
            'args': (7, 0)
        },
        {
            'percentage': 0.08,
            'function': mock_utils.last_seen_generator,
            'args': (365, 300)
        }
    ],
    MockNetworkDeviceProperties.SccmDevice: [
        {
            'percentage': 0.9,
            'function': mock_utils.last_seen_generator,
            'args': (7, 0)
        },
        {
            'percentage': 0.1,
            'function': mock_utils.last_seen_generator,
            'args': (365, 300)
        }
    ],
    MockNetworkDeviceProperties.QualysScansDevice: [
        {
            'percentage': 0.5,
            'function': mock_utils.last_seen_generator,
            'args': (7, 0)
        },
        {
            'percentage': 0.3,
            'function': mock_utils.last_seen_generator,
            'args': (30, 0)
        },
        {
            'percentage': 0.2,
            'function': mock_utils.last_seen_generator,
            'args': (365, 0)
        },
    ],
    MockNetworkDeviceProperties.CiscoMerakiDevice: [
        {
            'percentage': 0.9,
            'function': mock_utils.last_seen_generator,
            'args': (7, 0)
        },
        {
            'percentage': 0.08,
            'function': mock_utils.last_seen_generator,
            'args': (14, 7)
        },
        {
            'percentage': 0.02,
            'function': mock_utils.last_seen_generator,
            'args': (365, 14)
        },
    ],
    MockNetworkDeviceProperties.AWSDevice: [
        {
            'percentage': 1,
            'function': mock_utils.last_seen_generator,
            'args': (2, 0)
        },
    ],
    MockNetworkDeviceProperties.GCEDevice: [
        {
            'percentage': 1,
            'function': mock_utils.last_seen_generator,
            'args': (2, 0)
        },
    ],
    MockNetworkDeviceProperties.AzureDevice: [
        {
            'percentage': 1,
            'function': mock_utils.last_seen_generator,
            'args': (2, 0)
        },
    ],
    MockNetworkDeviceProperties.EsxDevice: [
        {
            'percentage': 1,
            'function': mock_utils.last_seen_generator,
            'args': (2, 0)
        },
    ],
    MockNetworkDeviceProperties.HyperVDevice: [
        {
            'percentage': 1,
            'function': mock_utils.last_seen_generator,
            'args': (2, 0)
        },
    ],
}

USERS_LAST_SEEN_STATS = {
    MockNetworkUserProperties.ADUser: [
        {
            'percentage': 0.7,
            'function': mock_utils.last_seen_generator,
            'args': (30, 0)
        },
        {
            'percentage': 0.2,
            'function': mock_utils.last_seen_generator,
            'args': (30 * 3, 0)
        },
        {
            'percentage': 0.1,
            'function': mock_utils.last_seen_generator,
            'args': (365, 0)
        }
    ]
}


def user_creator(i: int, network: MockNetwork, user: MockNetworkUser):
    user_full_name = network.get_random_name(i)
    username = '.'.join([name_part for name_part in user_full_name.split(' ')]).lower()
    user.username = f'{username}@{DOMAIN}'
    user.mail = f'{username}@{DOMAIN}'
    user.domain = DOMAIN
    user.employee_id = EMPLOYEE_ID_START + i
    user.user_telephone_number = f'+1-{random.randint(500, 600)}-{random.randint(1, 999)}-{random.randint(1, 9999)}'
    user.display_name = user_full_name
    user.first_name = user_full_name.split(' ')[0]
    user.last_name = user_full_name.split(' ')[1]
    user.user_city = random.choice(COMPANY_SITE_LOCATIONS)
    user.is_local = False
    user.is_locked = random.randint(1, 100) <= 5    # 5% of users are locked
    user.password_never_expires = random.randint(1, 1000) <= 5  # 0.5%
    user.password_not_required = random.randint(1, 1000) <= 2   # 0.2%
    user.account_disabled = random.randint(1, 100) <= 1  # 1% are disabled
    user.is_admin = random.randint(1, 1000) <= 5  # 0.5% are admins

    if random.randint(1, 100) <= 95:
        user.last_password_change = mock_utils.random_day_generator(30 * 3, 1)    # random day in the last 3 months
    else:
        user.last_password_change = mock_utils.random_day_generator(365, 90)  # random day last year but not last 3 mon

    # AD Specific
    ad_specific = AdAdapterParser.new_user_adapter()
    ad_specific.ad_sid = f'S-1-5-21-{random.randint(10000, 99999)}-{random.randint(1000000, 9999999)}'
    user.add_specific(MockNetworkUserProperties.ADUser, ad_specific)


def windows_device_creator(i: int, network: MockNetwork, device: MockNetworkDevice):
    # Generic Data
    user = network.get_random_name(i)
    device.last_used_users = [user]
    device.name = mock_utils.get_random_windows_pc_name(username=user)
    device.hostname = device.name
    device.add_nic(network.generate_mac(), [network.generate_ip()])
    device.domain = DOMAIN
    device.part_of_domain = True
    device.device_managed_by = mock_utils.get_random_manager_name()
    device.figure_os(mock_utils.get_random_windows_host_os())
    device.physical_location = random.choice(COMPANY_SITE_LOCATIONS)
    device.device_disabled = random.randint(1, 100) <= 1  # 1% are disabled
    for software in random.sample(mock_utils.get_random_software_list(), k=2):
        device.add_installed_software(**software)   # pylint: disable=not-a-mapping

    # Hardware
    device.total_physical_memory = random.choice([4, 8, 16])
    device.free_physical_memory = int(device.total_physical_memory * random.choice([0.1, 0.2, 0.3, 0.4, 0.5]))
    device.add_hd(
        total_size=random.choice([80, 160, 240]),
        free_size=random.choice([20, 40, 60])
    )

    # Set up cpu's
    device.total_number_of_cores = device.total_physical_memory / 4

    device.add_security_patch(security_patch_id='KB3199986')
    device.add_security_patch(security_patch_id='KB3200970')

    # 10% have potential updates
    if random.randint(1, 10) <= 1:
        for available_security_patches in mock_utils.get_random_windows_available_security_patches():
            device.add_available_security_patch(**available_security_patches)

    # Adapter-Specific data
    # AD
    ad_specific = AdAdapterParser.new_device_adapter()
    ad_specific.ad_is_dc = True
    device.add_specific(MockNetworkDeviceProperties.ADDevice, ad_specific)

    # Properties
    if random.randint(1, 10) <= 9:
        device.add_property(MockNetworkDeviceProperties.ADDevice)
        if random.randint(1, 100) <= 85:
            device.add_property(MockNetworkDeviceProperties.SccmDevice)
    if random.randint(1, 100) <= 90:
        device.add_property(MockNetworkDeviceProperties.CarbonBlackResponseDevice)
        device.add_specific(
            MockNetworkDeviceProperties.CarbonBlackResponseDevice,
            CarbonBlackResponseAdapterParser.new_device_adapter()
        )
    if random.randint(1, 10) <= 2:
        device.add_property(MockNetworkDeviceProperties.EsxDevice)
    if random.randint(1, 100) <= 85:
        device.add_property(MockNetworkDeviceProperties.QualysScansDevice)
    if random.randint(1, 100) <= 97:
        device.add_property(MockNetworkDeviceProperties.CiscoMerakiDevice)
    if random.randint(1, 100) <= 98:
        device.add_property(MockNetworkDeviceProperties.EpoDevice)

    if random.randint(1, 10) <= 4:
        device.add_property(MockNetworkDeviceProperties.SplunkDevice)
        splunk_specific = SplunkAdapterParser.new_device_adapter()
        splunk_specific.splunk_source = 'AD_DHCP'
        device.add_specific(MockNetworkDeviceProperties.SplunkDevice, splunk_specific)


# pylint: disable=too-many-statements
def linux_servers_creator(i: int, network: MockNetwork, device: MockNetworkDevice):
    # Lets generate a server name
    hostname = random.choice(['lab', 'infra', 'web', 'db', 'monitor', 'external'])
    hostname += random.choice(['nginx-', 'apache-', 'sql-', 'mongo-', 'lb-', '', '', ''])
    hostname += str(random.randint(100, 999)) + '-' + random.choice(['prd', 'prod', 'dev', 'stg', 'beta'])

    device.name = hostname
    device.hostname = hostname + f'.{DOMAIN}'
    device.figure_os(mock_utils.get_random_linux_os_host())

    device.total_physical_memory = random.choice([4, 8, 16, 32])
    device.free_physical_memory = int(device.total_physical_memory * random.choice([0.1, 0.2, 0.3, 0.4, 0.5]))
    device.add_hd(
        total_size=random.choice([80, 160, 240]),
        free_size=random.choice([20, 40, 60])
    )
    device.physical_location = random.choice(COMPANY_SITE_LOCATIONS)
    device.device_managed_by = mock_utils.get_random_manager_name()

    device.device_manufacturer = random.choice(['intel', 'amd', 'dell'])
    device.device_serial = uuid.uuid4()
    device.total_number_of_physical_processors = device.total_physical_memory / 4
    device.total_number_of_cores = device.total_physical_memory / 2
    device.swap_total = random.randint(10, 16)
    device.swap_free = round(device.swap_total * random.choice([0.4, 0.5, 0.6, 0.7]), 2)

    for software in random.sample(mock_utils.get_random_linux_software_list(), k=5):
        device.add_installed_software(**software)   # pylint: disable=not-a-mapping

    # Put list of installed linux software

    # add properties here
    host_platform = random.choices(
        [
            MockNetworkDeviceProperties.AWSDevice,
            MockNetworkDeviceProperties.EsxDevice
        ],
        weights=[0.7, 0.3]
    )[0]
    device.add_property(host_platform)

    if random.randint(1, 10) <= 9:
        device.add_property(MockNetworkDeviceProperties.ChefDevice)

    if random.randint(1, 10) <= 9 and \
            host_platform not in [MockNetworkDeviceProperties.GCEDevice, MockNetworkDeviceProperties.AzureDevice]:
        # Qualys doesn't scan azure and gce
        device.add_property(MockNetworkDeviceProperties.QualysScansDevice)

    if random.randint(1, 100) <= 94:
        device.add_property(MockNetworkDeviceProperties.CiscoMerakiDevice)

    if random.randint(1, 100) <= 90:
        device.add_property(MockNetworkDeviceProperties.CarbonBlackResponseDevice)
        device.add_specific(
            MockNetworkDeviceProperties.CarbonBlackResponseDevice,
            CarbonBlackResponseAdapterParser.new_device_adapter()
        )
    if random.randint(1, 100) <= 97:
        device.add_property(MockNetworkDeviceProperties.EpoDevice)

    # IP's
    ips = [network.generate_ip()]
    if random.randint(1, 10) <= 4 and host_platform == MockNetworkDeviceProperties.AWSDevice:
        # only cloud instances get public ip. should be 40% * (0.5 for all cloud ) == 20% of devices
        public_ip = network.generate_public_ip()
        ips.append(public_ip)
    else:
        public_ip = None
    device.add_nic(network.generate_mac(), ips)

    # specific
    chef_specific = ChefAdapterParser.new_device_adapter()
    chef_specific.public_ip = public_ip

    aws_specific = AwsAdapterParser.new_device_adapter()
    aws_specific.aws_region = random.choice(['us-east-1', 'us-east-2'])
    aws_specific.public_ip = public_ip
    aws_specific.instance_type = {
        4: 't2.medium',  # 4gb 2cores. we have 1
        8: random.choice(['t2.large', 'm4.large']),
        16: random.choice(['t2.xlarge', 'm4.xlarge']),
        32: random.choice(['t2.2xlarge', 'm4.2xlarge'])
    }.get(device.total_physical_memory)
    aws_specific.aws_device_type = 'EC2'
    aws_specific.key_name = f'aws-key-{random.randint(1, 50)}'
    aws_specific.vpc_name = f'{DOMAIN}-private-vpc'
    aws_specific.vpc_id = f'vpc-122d3fd3'
    aws_specific.subnet_name = f'{DOMAIN}-main-subnet'
    aws_specific.subnet_id = f'subnet-1742dd2e'
    aws_specific.launch_time = mock_utils.random_day_generator(365, 5)
    if random.randint(1, 10) <= 3:
        aws_specific.add_aws_security_group(
            name='ALL',
            inbound=[AWSIPRule(ip_protocol='Any', ip_ranges=['0.0.0.0/0'])],
            outbound=[AWSIPRule(ip_protocol='Any', ip_ranges=['0.0.0.0/0'])]
        )
    else:
        aws_specific.add_aws_security_group(
            name='ALL',
            inbound=[AWSIPRule(ip_protocol='Any', ip_ranges=['10.0.0.0/0'])],
            outbound=[AWSIPRule(ip_protocol='Any', ip_ranges=['10.0.0.0/0'])]
        )

    device.add_specific(MockNetworkDeviceProperties.ChefDevice, chef_specific)
    device.add_specific(MockNetworkDeviceProperties.AWSDevice, aws_specific)


def set_epo_isolated(device: MockNetworkDevice):
    # Prepare the isolating adapterdata part
    cbr_device = device.get_specific(MockNetworkDeviceProperties.CarbonBlackResponseDevice)
    if not cbr_device:
        cbr_device = CarbonBlackResponseAdapterParser.new_device_adapter()
        device.add_specific(MockNetworkDeviceProperties.CarbonBlackResponseDevice, cbr_device)

    # If we don't have EPO, or we have it but it was not seen in the past week, set isolating
    epo_specific = device.get_specific(MockNetworkDeviceProperties.EpoDevice)
    if not device.does_have_property(MockNetworkDeviceProperties.EpoDevice) or \
            (epo_specific and epo_specific.last_seen < (datetime.now() - timedelta(days=7))):
        cbr_device.is_isolating = True


def main():
    network = MockNetwork()
    manager = MockManager()

    print(f'[+] Creating users')
    network.generate_random_names(USERS_IN_NETWORK)
    ids = network.create_users(USERS_IN_NETWORK, user_creator)

    print(f'[+] Setting user existence')
    network.set_users_properties(ids, USER_EXISTENCE_STATS)

    print(f'[+] Setting users last seen')
    network.set_users_attributes(ids, USERS_LAST_SEEN_STATS)

    print(f'[+] Creating devices')
    ids = network.create_devices(WINDOWS_DEVICES_IN_NETWORK, windows_device_creator)
    ids += network.create_devices(LINUX_DEVICES_IN_NETWORK, linux_servers_creator)

    print(f'[+] Setting last seen')
    network.set_devices_attributes(ids, LAST_SEEN_STATS)

    print(f'[+] Setting some epo isolated')
    network.update_devices(ids, set_epo_isolated)

    manager.create_demo_from_network(network)
