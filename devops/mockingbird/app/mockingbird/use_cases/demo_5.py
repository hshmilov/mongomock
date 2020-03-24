import random

import uuid

from mockingbird.commons import mock_utils
from mockingbird.commons.mock_network import MockNetwork
from mockingbird.commons.mock_network_device import MockNetworkDevice, MockNetworkDeviceProperties
from mockingbird.commons.mock_network_user import MockNetworkUserProperties, MockNetworkUser
from mockingbird.mock_adapters.aws import AwsAdapterParser
from mockingbird.mock_adapters.azure import AzureAdapterParser
from mockingbird.mock_adapters.mobileiron import MobileironAdapterParser
from mockingbird.mock_adapters.sccm import SccmAdapterParser
from mockingbird.mock_manager import MockManager
from mockingbird.mock_adapters.ad import AdAdapterParser


DOMAIN = 'demo.local'
EMPLOYEE_ID_START = 880000
COMPANY_SITE_LOCATIONS = ['Columbus', 'Richmond', 'New York', 'Boston']
WINDOWS_DEVICES_IN_NETWORK = 22849  # Number of devices in network
LINUX_DEVICES_IN_NETWORK = 14412
IOS_DEVICES_IN_NETWORK = 1397
ANDROID_DEVICES_IN_NETWORK = 812
WEIRD_DEVICES_IN_NETWORK = 10
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
            'percentage': 0.999,
            'function': mock_utils.last_seen_generator,
            'args': (7, 0)
        },
        {
            'percentage': 0.001,
            'function': mock_utils.last_seen_generator,
            'args': (365, 300)
        }
    ],
    MockNetworkDeviceProperties.EpoDevice: [
        {
            'percentage': 0.999,
            'function': mock_utils.last_seen_generator,
            'args': (6, 0)
        },
        {
            'percentage': 0.001,
            'function': mock_utils.last_seen_generator,
            'args': (365, 30)
        }
    ],
    MockNetworkDeviceProperties.CarbonBlackResponseDevice: [
        {
            'percentage': 0.99,
            'function': mock_utils.last_seen_generator,
            'args': (7, 0)
        },
        {
            'percentage': 0.01,
            'function': mock_utils.last_seen_generator,
            'args': (365, 30)
        }
    ],
    MockNetworkDeviceProperties.ChefDevice: [
        {
            'percentage': 0.992,
            'function': mock_utils.last_seen_generator,
            'args': (7, 0)
        },
        {
            'percentage': 0.008,
            'function': mock_utils.last_seen_generator,
            'args': (365, 300)
        }
    ],
    MockNetworkDeviceProperties.EclypsiumDevice: [
        {
            'percentage': 0.992,
            'function': mock_utils.last_seen_generator,
            'args': (7, 0)
        },
        {
            'percentage': 0.008,
            'function': mock_utils.last_seen_generator,
            'args': (365, 300)
        }
    ],
    MockNetworkDeviceProperties.SccmDevice: [
        {
            'percentage': 0.99,
            'function': mock_utils.last_seen_generator,
            'args': (7, 0)
        },
        {
            'percentage': 0.01,
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
            'percentage': 0.49,
            'function': mock_utils.last_seen_generator,
            'args': (30, 0)
        },
        {
            'percentage': 0.01,
            'function': mock_utils.last_seen_generator,
            'args': (365, 30)
        },
    ],
    MockNetworkDeviceProperties.TenableSC: [
        {
            'percentage': 0.5,
            'function': mock_utils.last_seen_generator,
            'args': (7, 0)
        },
        {
            'percentage': 0.49,
            'function': mock_utils.last_seen_generator,
            'args': (30, 0)
        },
        {
            'percentage': 0.01,
            'function': mock_utils.last_seen_generator,
            'args': (365, 30)
        },
    ],
    MockNetworkDeviceProperties.CiscoMerakiDevice: [
        {
            'percentage': 0.99,
            'function': mock_utils.last_seen_generator,
            'args': (7, 0)
        },
        {
            'percentage': 0.008,
            'function': mock_utils.last_seen_generator,
            'args': (14, 7)
        },
        {
            'percentage': 0.002,
            'function': mock_utils.last_seen_generator,
            'args': (365, 14)
        },
    ],
    MockNetworkDeviceProperties.CounteractDevice: [
        {
            'percentage': 0.99,
            'function': mock_utils.last_seen_generator,
            'args': (7, 0)
        },
        {
            'percentage': 0.008,
            'function': mock_utils.last_seen_generator,
            'args': (14, 7)
        },
        {
            'percentage': 0.002,
            'function': mock_utils.last_seen_generator,
            'args': (365, 14)
        },
    ],
    MockNetworkDeviceProperties.MobileironDevice: [
        {
            'percentage': 0.99,
            'function': mock_utils.last_seen_generator,
            'args': (7, 0)
        },
        {
            'percentage': 0.008,
            'function': mock_utils.last_seen_generator,
            'args': (14, 7)
        },
        {
            'percentage': 0.002,
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


def android_device_generator(i: int, network: MockNetwork, device: MockNetworkDevice):
    # Lets generate a server name
    ips = [network.generate_ip()]
    device.add_nic(network.generate_mac(), ips)
    user = network.get_user_by_id(i)
    device.email = user.mail

    if user.first_name:
        device.name = f'{user.first_name.capitalize()}\'s Android'

    if random.randint(1, 10) <= 5:
        device.device_manufacturer = 'Samsung'
        device.device_model = random.choice([
            'SM-G920F',
            'SM-G930F',
            'SM-G935F',
            'SM-G945F',
            'SM-G950F',
            'SM-J600G',
            'SM-G973F'
        ])
    elif random.randint(1, 10) <= 3:
        device.device_manufacturer = 'Oneplus'
        device.device_model = random.choice([
            'A6000',
            'A5010',
            'A6010',
            'A3003'
        ])

    else:
        device.device_manufacturer = 'Redmi'
        device.device_model = random.choice([
            'Note 5 Pro'
            'Note 4',
            'Note 8 Pro',
            'Note 7 Pro',
            'Note 6 Pro'
        ])

    if device.device_model == 'SM-G973F':
        device.figure_os('Android 10.0.0')
    else:
        device.figure_os(
            'Android ' + random.choices(
                ['9.0.0', '8.1.0', '8.0.0', '7.1.2', '7.1.1'],
                weights=[0.5, 0.18, 0.12, 0.15, 0.05]
            )[0]
        )

    mobileiron_specific = MobileironAdapterParser.new_device_adapter()
    mobileiron_specific.user_first_name = user.first_name
    mobileiron_specific.user_last_name = user.last_name
    mobileiron_specific.display_name = user.display_name
    mobileiron_specific.current_phone_number = user.user_telephone_number
    mobileiron_specific.device_encrypted = bool(random.randint(1, 100) > 2)

    device.add_specific(MockNetworkDeviceProperties.AzureDevice, mobileiron_specific)

    if random.randint(1, 100) <= 92:
        device.add_property(MockNetworkDeviceProperties.MobileironDevice)
        if random.randint(1, 100) <= 92:
            device.add_property(MockNetworkDeviceProperties.CiscoMerakiDevice)
            device.add_property(MockNetworkDeviceProperties.CounteractDevice)
        elif random.randint(1, 100) <= 4:
            device.add_property(MockNetworkDeviceProperties.CiscoMerakiDevice)
    else:
        device.add_property(MockNetworkDeviceProperties.CiscoMerakiDevice)


def ios_device_generator(i: int, network: MockNetwork, device: MockNetworkDevice):
    user = network.get_user_by_id(i + ANDROID_DEVICES_IN_NETWORK + 1000)
    ips = [network.generate_ip()]
    device.add_nic(network.generate_mac(), ips)

    device.email = user.mail
    if user.first_name:
        device.name = f'{user.first_name.capitalize()}\'s iPhone'

    device.device_manufacturer = 'Apple'
    device.device_model = random.choice([
        'iPhone10,4',
        'iPhone9,3',
        'iPhone11,8',
        'iPhone8,1',
        'iPhone7.2',
        'iPhone10,1',
        'iPhone11,6'
    ])

    device.figure_os(
        'iOS ' + random.choices(
            ['13.3.1', '12.4.5', '12.4.1', '13.2.3', '13.1.3'],
            weights=[0.5, 0.18, 0.12, 0.15, 0.05]
        )[0]
    )

    mobileiron_specific = MobileironAdapterParser.new_device_adapter()
    mobileiron_specific.user_first_name = user.first_name
    mobileiron_specific.user_last_name = user.last_name
    mobileiron_specific.display_name = user.display_name
    mobileiron_specific.current_phone_number = user.user_telephone_number
    mobileiron_specific.device_encrypted = bool(random.randint(1, 100) > 3)

    device.add_specific(MockNetworkDeviceProperties.AzureDevice, mobileiron_specific)

    if random.randint(1, 100) <= 92:
        device.add_property(MockNetworkDeviceProperties.MobileironDevice)
        if random.randint(1, 100) <= 92:
            device.add_property(MockNetworkDeviceProperties.CiscoMerakiDevice)
            device.add_property(MockNetworkDeviceProperties.CounteractDevice)
        elif random.randint(1, 100) <= 4:
            device.add_property(MockNetworkDeviceProperties.CiscoMerakiDevice)
    else:
        device.add_property(MockNetworkDeviceProperties.CiscoMerakiDevice)


def windows_device_creator(i: int, network: MockNetwork, device: MockNetworkDevice):
    # Generic Data
    user = network.get_user_by_id(i)
    device.last_used_users = [user.username]
    ip = network.generate_ip()
    device.name = mock_utils.get_random_windows_pc_name(username=user.display_name)
    device.hostname = device.name
    device.add_nic(network.generate_mac(), [ip])
    device.domain = DOMAIN
    device.part_of_domain = True
    device.device_managed_by = mock_utils.get_random_manager_name()
    device.figure_os(mock_utils.get_random_windows_host_os())
    device.physical_location = random.choice(COMPANY_SITE_LOCATIONS)
    device.device_disabled = random.randint(1, 100) <= 1  # 1% are disabled

    if random.randint(1, 100) <= 80:
        device.figure_os(random.choice(['Windows 10 Pro 64-bit']))
        device.os.build = random.choice(['18362.720', '18363.720'])

        if random.randint(1, 100) <= 90:
            device.add_security_patch(security_patch_id='KB4551762')

    elif random.randint(1, 100) <= 18:
        device.figure_os(random.choice(['Windows Server 2016 64-bit', 'Windows Server 2019 64-bit']))
        ad_specific = AdAdapterParser.new_device_adapter()
        ad_specific.ad_is_dc = True
        device.add_specific(MockNetworkDeviceProperties.ADDevice, ad_specific)
    else:
        device.figure_os('Windows XP 64-bit')

    for software in random.sample(mock_utils.get_random_software_list(), k=2):
        device.add_installed_software(**software)   # pylint: disable=not-a-mapping

    if random.randint(1, 1000) <= 8:  # 0.008
        for software in random.sample(mock_utils.get_random_software_vulnerable_list(), k=1):
            device.add_installed_software(**software)

    if random.randint(1, 10) <= 5:  # 50% have chrome
        if random.randint(1, 1000) < 4:   # 0.004 * 0.5 = 0.002 (0.2%) have old chrome with a cve
            device.add_installed_software(name='Google Chrome', version='65.0.3325.147', vendor='Google Inc.')
        else:
            device.add_installed_software(name='Google Chrome', version='80.0.3987.132', vendor='Google Inc.')

    for port in [135, 139, 445]:
        device.add_open_port(port_id=port, protocol='TCP')
    if random.randint(1, 10) <= 2:
        for port in random.sample([443, 80, 21, 25, 2201], k=2):
            device.add_open_port(port_id=port, protocol='TCP')

    # Hardware
    device.total_physical_memory = random.choice([4, 8, 16])
    device.free_physical_memory = int(device.total_physical_memory * random.choice([0.1, 0.2, 0.3, 0.4, 0.5]))
    device.add_hd(
        total_size=random.choice([80, 160, 240]),
        free_size=random.choice([20, 40, 60])
    )

    # Set up cpu's
    device.total_number_of_cores = device.total_physical_memory / 4

    # Pure general info things
    device.add_security_patch(security_patch_id='KB3199986')
    device.add_security_patch(security_patch_id='KB3200970')

    # 10% have potential updates
    if random.randint(1, 10) <= 1:
        for available_security_patches in mock_utils.get_random_windows_available_security_patches():
            device.add_available_security_patch(**available_security_patches)

    # They all have the same users
    device.add_users(
        user_sid=user.get_specific(MockNetworkUserProperties.ADUser).ad_sid,
        username=user.username,
        is_local=False,
        is_admin=user.is_admin,
        last_use_date=user.last_seen
    )

    device.add_users(
        user_sid=f'S-1-5-21-{random.randint(10000, 99999)}-{random.randint(1000000, 9999999)}',
        username=f'Administrator@{device.name.upper()}',
        is_local=True,
        is_admin=True,
        is_disabled=False,
    )

    is_guest_admin = True if random.randint(1, 1000) <= 1 else False
    device.add_users(
        user_sid=f'S-1-5-21-{random.randint(10000, 99999)}-{random.randint(1000000, 9999999)}',
        username=f'Guest@{device.name.upper()}',
        is_local=True,
        is_admin=False,
        is_disabled=is_guest_admin,
    )

    device.add_local_admin(admin_name=f'Domain Admins@{DOMAIN}', admin_type='Group Membership')
    device.add_local_admin(admin_name=f'Administrator@{device.name.upper()}', admin_type='Admin User')
    if is_guest_admin:
        device.add_local_admin(admin_name=f'Guest@{device.name.upper()}', admin_type='Admin User')
    if user.is_admin:
        device.add_local_admin(admin_name=user.username, admin_type='Admin User')

    hardware_list = mock_utils.get_random_hardware_list()
    for hardware in random.sample(hardware_list, k=int(len(hardware_list) * 0.9)):
        device.add_connected_hardware(**hardware)   # pylint: disable=not-a-mapping

    shares_list = mock_utils.get_random_shares_list()
    for share in random.sample(shares_list, k=int(len(shares_list) * 0.9)):
        device.add_share(**share)  # pylint: disable=not-a-mapping

    processes_list = mock_utils.get_random_processes_list()
    for process in random.sample(processes_list, k=int(len(processes_list) * 0.9)):
        device.add_process(**process)  # pylint: disable=not-a-mapping

    services_list = mock_utils.get_random_services_list()
    for service in random.sample(services_list, k=int(len(services_list) * 0.9)):
        device.add_service(**service)  # pylint: disable=not-a-mapping

    # Do not have general info
    device.add_property(MockNetworkDeviceProperties.NoGeneralInfo)

    sccm_specific = SccmAdapterParser.new_device_adapter()

    # Properties
    if random.randint(1, 1000) <= 994:
        device.add_property(MockNetworkDeviceProperties.ADDevice)
        if random.randint(1, 100) <= 95:
            device.add_property(MockNetworkDeviceProperties.SccmDevice)
    if random.randint(1, 10) <= 2:
        device.add_property(MockNetworkDeviceProperties.EsxDevice)
        sccm_specific.chasis_value = 'Virtual Machine'
    if random.randint(1, 100) <= 85:
        device.add_property(MockNetworkDeviceProperties.TenableSC)
    if random.randint(1, 100) <= 92:
        device.add_property(MockNetworkDeviceProperties.CounteractDevice)
        device.add_property(MockNetworkDeviceProperties.CiscoMerakiDevice)
    else:
        if random.randint(1, 2) == 1:
            device.add_property(MockNetworkDeviceProperties.CiscoMerakiDevice)
    if random.randint(1, 100) <= 92:
        device.add_property(MockNetworkDeviceProperties.EclypsiumDevice)

    if random.randint(1, 1000) <= 996:
        device.add_property(MockNetworkDeviceProperties.EpoDevice)
        device.add_installed_software(name='McAfee ePO', version='5.9.0.732', vendor='McAfee')
    else:
        # from the windows devices on which EPO is not installed, take 10% of devices,
        # and still put  it in the installed software list.
        if random.randint(1, 100) <= 10:
            device.add_installed_software(name='McAfee ePO', version='5.9.0.732', vendor='McAfee')

    device.add_specific(MockNetworkDeviceProperties.SccmDevice, sccm_specific)


# pylint: disable=too-many-statements
def linux_servers_creator(i: int, network: MockNetwork, device: MockNetworkDevice):
    # Lets generate a server name
    hostname = random.choice(['lab', 'infra', 'web', 'db', 'monitor', 'external'])
    hostname += random.choice(['nginx-', 'apache-', 'sql-', 'mongo-', 'lb-', '', '', ''])
    hostname += str(i + 17134) + '-' + random.choice(['prd', 'prod', 'dev', 'stg', 'beta'])

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

    # add properties here
    host_platform = random.choices(
        [
            MockNetworkDeviceProperties.AzureDevice,
            MockNetworkDeviceProperties.AWSDevice,
            MockNetworkDeviceProperties.EsxDevice
        ],
        weights=[0.5, 0.2, 0.3]
    )[0]
    device.add_property(host_platform)

    if random.randint(1, 100) <= 95:
        # 5% of linuxes are not known. They are simply machines on ESX or AWS or Azure.
        if random.randint(1, 10) <= 8:
            device.add_property(MockNetworkDeviceProperties.TenableSC)

        if random.randint(1, 100) <= 90:
            device.add_property(MockNetworkDeviceProperties.EpoDevice)

    if host_platform == MockNetworkDeviceProperties.EsxDevice:
        if random.randint(1, 100) <= 5:
            device.add_property(MockNetworkDeviceProperties.CiscoMerakiDevice)
        else:
            if random.randint(1, 10) <= 8:
                device.add_property(MockNetworkDeviceProperties.CounteractDevice)
            if random.randint(1, 10) <= 8:
                device.add_property(MockNetworkDeviceProperties.CiscoMerakiDevice)

    # IP's
    ips = [network.generate_ip()]
    if random.randint(1, 10) <= 3 and host_platform in [
        MockNetworkDeviceProperties.AzureDevice,
        MockNetworkDeviceProperties.AWSDevice
    ]:
        # only cloud instances get public ip.
        public_ip = network.generate_public_ip()
        ips.append(public_ip)
    else:
        public_ip = None
    device.add_nic(network.generate_mac(), ips)

    # Azure specific
    azure_specific = AzureAdapterParser.new_device_adapter()
    azure_specific.location = random.choice(['eastus', 'eastus2', 'northcentralus', 'westus2'])
    if public_ip:
        azure_specific.add_public_ip(public_ip)
    azure_specific.instance_type = {
        4: 'Standard_F2s',
        8: 'Standard_D2s_v3',
        16: 'Standard_D4s_v3',
        32: 'Standard_D8s_v3'
    }.get(device.total_physical_memory)
    azure_specific.admin_username = device.device_managed_by.lower().replace(' ', '_')

    # AWS Specific
    aws_specific = AwsAdapterParser.new_device_adapter()
    aws_specific.aws_region = random.choice(['us-east-1', 'us-east-2'])
    if public_ip:
        aws_specific.add_public_ip(public_ip)
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

    if random.randint(1, 10) <= 1:
        azure_specific.add_firewall_rule(
            name='TEST FW - Allow ALL',
            source='Azure Firewall Rule',
            type='Allow',
            direction='INGRESS',
            target='0.0.0.0/0',
            protocol='Any',
            from_port=0,
            to_port=65535
        )

        aws_specific.add_firewall_rule(
            name='Default Security Group',
            source='AWS Instance Security Group',
            type='Allow',
            direction='INGRESS',
            target='0.0.0.0/0',
            protocol='Any',
            from_port=0,
            to_port=65535
        )
    else:
        azure_specific.add_firewall_rule(
            name='Allow from management network',
            source='Azure Firewall Rule',
            type='Allow',
            direction='INGRESS',
            target='10.99.4.0/24',
            protocol='Any',
            from_port=0,
            to_port=65535
        )

        aws_specific.add_firewall_rule(
            name='Management Security Group',
            source='AWS Instance Security Group',
            type='Allow',
            direction='INGRESS',
            target='10.99.4.0/24',
            protocol='Any',
            from_port=0,
            to_port=65535
        )
    device.add_specific(MockNetworkDeviceProperties.AzureDevice, azure_specific)
    device.add_specific(MockNetworkDeviceProperties.AWSDevice, aws_specific)


def weird_devices_creator(i: int, network: MockNetwork, device: MockNetworkDevice):
    # Lets generate a server name
    ips = [network.generate_ip()]
    device.add_nic(network.generate_mac(mac_type='china-mobile-iot'), ips)
    device.add_property(MockNetworkDeviceProperties.CiscoMerakiDevice)


def main():
    network = MockNetwork(ip_start='10.0.48.12')
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

    print(f'[+] Creating iOS / Android devices')
    ids += network.create_devices(ANDROID_DEVICES_IN_NETWORK, android_device_generator)
    ids += network.create_devices(IOS_DEVICES_IN_NETWORK, ios_device_generator)

    print(f'[+] Creating weird devices')
    ids += network.create_devices(WEIRD_DEVICES_IN_NETWORK, weird_devices_creator)

    print(f'[+] Setting last seen')
    network.set_devices_attributes(ids, LAST_SEEN_STATS)

    manager.create_demo_from_network(network)
