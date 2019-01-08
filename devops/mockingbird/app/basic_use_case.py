#!/usr/local/bin/python3
# pylint: disable=protected-access, deprecated-module, too-many-statements
import string
import sys
import random

from datetime import datetime, timedelta
from typing import List
from uuid import uuid4

from env_utils import create_my_device_adapter, ip2int, int2ip
from mock_manager import MockManager

from axonius.devices.device_adapter import DeviceAdapter, AdapterProperty

NUMBER_OF_DEVICES_AD = 107524
NUMBER_OF_DEVICES_AD_DC = 10
NUMBER_OF_DEVICES_EPO = NUMBER_OF_DEVICES_AD - 102
NUMBER_OF_DEVICES_SCCM = NUMBER_OF_DEVICES_AD - 178
NUMBER_OF_DEVICES_TANIUM = NUMBER_OF_DEVICES_AD - 251
NUMBER_OF_DEVICES_QUALYS = NUMBER_OF_DEVICES_AD - 421

AD_PERCENTAGE_OF_SHORT_LAST_SEEN_RANGE = 0.95
AD_SHORT_LAST_SEEN_RANGE_IN_DAYS = 14
AD_LONG_LAST_SEEN_RANGE_IN_DAYS = 365

AGENTS_PERCENTAGE_OF_SHORT_LAST_SEEN_RANGE = 0.95
AGENTS_SHORT_LAST_SEEN_RANGE_IN_DAYS = 5
AGENTS_LONG_LAST_SEEN_RANGE_IN_DAYS = 365


def set_agents_last_seen(agents):
    num_of_agent_devices_with_sort_range_last_seen = int(len(agents) * AGENTS_PERCENTAGE_OF_SHORT_LAST_SEEN_RANGE)
    for device in agents[:num_of_agent_devices_with_sort_range_last_seen]:
        device.last_seen = datetime.now() - \
            timedelta(
            days=random.randint(0, AGENTS_SHORT_LAST_SEEN_RANGE_IN_DAYS),
            seconds=random.randint(0, 59),
            minutes=random.randint(0, 59),
            hours=random.randint(0, 18)
        )
    for device in agents[num_of_agent_devices_with_sort_range_last_seen:]:
        device.last_seen = datetime.now() - \
            timedelta(
            days=random.randint(0, AGENTS_LONG_LAST_SEEN_RANGE_IN_DAYS),
            seconds=random.randint(0, 59),
            minutes=random.randint(0, 59),
            hours=random.randint(0, 18)
        )


def create_ad_devices():
    devices = []
    current_ip = ip2int('10.1.0.1')
    managers_names = [
        'Ryan Duffy',
        'Donald Deshong',
        'Joel Turner',
        'Carl Pein',
        'Danielle Lance',
        'Brandy Bumgarner',
        'Floyd Brady',
        'Mary Signs',
        'William Saari',
        'Charles Woods']
    for i in range(NUMBER_OF_DEVICES_AD):
        if i % 5000 == 0:
            print(f'Generated {i} AD devices')
        device = create_my_device_adapter('active_directory')
        device.name = random.choice(['PC-', 'DESKTOP-', 'WIN-']) + \
            ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
        device.id = f'CN={device.name},OU=Computers,DC=consto,DC=com'
        device.part_of_domain = True
        device.domain = 'consto.com'
        device.hostname = f'{device.name}.consto.com'
        device.name = device.hostname
        device.figure_os(
            random.choice(
                [
                    'Windows 10 Pro', 'Windows 10 Home', 'Windows 10 Enterprise',
                    'Windows 8.1 Pro', 'Windows 8.1 Enterprise',
                    'Windows 8',
                    'Windows 7 Enterprise', 'Windows 7 Ultimate',
                    'Windows Vista Business', 'Windows Vista Enterprise'
                ]
            )
        )
        ip = int2ip(current_ip)
        current_ip += 1
        device.add_nic(ips=[ip])
        device.device_managed_by = random.choice(managers_names)
        device.ad_site_location = random.choices(['Columbus', 'Richmond', 'New York', 'Boston'])
        device.ad_site_name = f'{device.ad_site_location}-Network'
        device.adapter_properties = [AdapterProperty.Assets.name, AdapterProperty.Manager.name]
        device.set_raw(device.to_dict())

        devices.append(device)

    num_of_ad_devices_with_sort_range_last_seen = int(NUMBER_OF_DEVICES_AD * AD_PERCENTAGE_OF_SHORT_LAST_SEEN_RANGE)
    for device in devices[:num_of_ad_devices_with_sort_range_last_seen]:
        device.last_seen = datetime.now() - timedelta(
            days=random.randint(0, AD_SHORT_LAST_SEEN_RANGE_IN_DAYS),
            seconds=random.randint(0, 59),
            minutes=random.randint(0, 59),
            hours=random.randint(0, 18)
        )
    for device in devices[num_of_ad_devices_with_sort_range_last_seen:]:
        device.last_seen = datetime.now() - timedelta(
            days=random.randint(0, AD_LONG_LAST_SEEN_RANGE_IN_DAYS),
            seconds=random.randint(0, 59),
            minutes=random.randint(0, 59),
            hours=random.randint(0, 18)
        )

    for i in range(NUMBER_OF_DEVICES_AD_DC):
        device = create_my_device_adapter('active_directory')
        device.name = f'SRVDC-{i+1}'
        device.id = f'CN={device.name},OU=Domain Controllers,DC=consto,DC=com'
        device.part_of_domain = True
        device.domain = 'consto.com'
        device.hostname = f'{device.name}.consto.com'
        device.name = device.hostname
        device.figure_os(
            random.choice(
                [
                    'Windows Server 2016', 'Windows Server 2012 R2', 'Windows Server 2012', 'Windows Server 2008 R2'
                ]
            )
        )
        is_device_srvdc1 = device.name == 'SRVDC-1'
        device.ad_is_dc = True
        device.ad_site_location = ['Columbus', 'Richmond', 'New York', 'Boston'][i % 4]
        device.ad_site_name = f'{device.ad_site_location}-Network'
        device.ad_dc_gc = is_device_srvdc1
        device.ad_dc_infra_master = is_device_srvdc1
        device.ad_dc_rid_master = is_device_srvdc1
        device.ad_dc_pdc_emulator = is_device_srvdc1
        device.ad_dc_naming_master = is_device_srvdc1
        device.ad_dc_schema_master = is_device_srvdc1
        device.ad_is_exchange_server = True
        ip = int2ip(current_ip)
        current_ip += 1
        device.add_nic(ips=[ip])
        device.last_seen = datetime.now() - timedelta(
            seconds=random.randint(0, 59),
            minutes=random.randint(0, 59),
            hours=random.randint(0, 18)
        )
        device.device_managed_by = random.choice(managers_names)
        device.set_raw(device.to_dict())

        devices.append(device)

    return devices


def create_sccm_from_ad(ad_devices: List[DeviceAdapter]):
    list_of_softwares = [
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
        {
            'vendor': 'Adobe Systems Incorporated',
            'name': 'Adobe Flash Player 30 PPAPI',
            'version': '30.0.0.113'
        }
    ]
    sccm_devices = []
    for i, ad_device in enumerate(ad_devices):
        if i % 5000 == 0:
            print(f'Generated {i} SCCM devices')
        device = create_my_device_adapter('sccm')
        device.name = ad_device.name
        device.hostname = ad_device.hostname
        device.id = f'SCCM_{device.hostname}'
        device.part_of_domain = ad_device.part_of_domain
        device.domain = ad_device.domain
        device._dict['os'] = ad_device._dict['os'].to_dict().copy()
        ad_ip = ad_device.network_interfaces[0].ips[0]

        mac_address = random.choice([
            '50:9A:4C:',    # dell
            '38:DE:AD:'     # intel
        ]) + '{:02X}:{:02X}:{:02X}'.format(*map(int, ad_ip.split('.')[1:]))
        device.add_nic(ips=[ad_ip], mac=mac_address)

        device.total_physical_memory = random.choice([4, 8, 16])

        software_i = random.randint(0, len(list_of_softwares) - 2)
        device.add_installed_software(**list_of_softwares[software_i])
        device.add_installed_software(**list_of_softwares[software_i + 1])
        device.adapter_properties = [AdapterProperty.Agent.name]

        device.set_raw(device.to_dict())

        sccm_devices.append(device)

    set_agents_last_seen(sccm_devices)

    return sccm_devices


def create_epo_from_ad(ad_devices: List[DeviceAdapter]):
    epo_devices = []
    for i, ad_device in enumerate(ad_devices):
        if i % 5000 == 0:
            print(f'Generated {i} EPO devices')
        device = create_my_device_adapter('epo')
        device.name = f'agent-{ad_device.name}'
        device.hostname = ad_device.hostname.split('.')[0]
        device.id = f'EPO_{device.hostname}'
        device._dict['os'] = ad_device._dict['os'].to_dict().copy()
        ad_ip = ad_device.network_interfaces[0].ips[0]

        device.add_nic(ips=[ad_ip])

        device.add_hd(
            total_size=random.choice([80, 160, 240]),
            free_size=random.choice([20, 40, 60])
        )

        device.adapter_properties = [
            AdapterProperty.Endpoint_Protection_Platform.name, AdapterProperty.Agent.name, AdapterProperty.Manager.name
        ]

        device.set_raw(device.to_dict())
        epo_devices.append(device)

    set_agents_last_seen(epo_devices)

    return epo_devices


def create_tanium_from_ad(ad_devices: List[DeviceAdapter]):
    tanium_devices = []
    for i, ad_device in enumerate(ad_devices):
        if i % 5000 == 0:
            print(f'Generated {i} Tanium devices')
        device = create_my_device_adapter('tanium')
        device.name = f'tanium-{ad_device.name}'
        device.hostname = ad_device.hostname.split('.')[0]
        device.id = f'Tanium_{device.hostname}'
        device._dict['os'] = ad_device._dict['os'].to_dict().copy()
        ad_ip = ad_device.network_interfaces[0].ips[0]
        device.add_nic(ips=[ad_ip])

        device.adapter_properties = [AdapterProperty.Agent.name]
        device.agent_version = '7.2' if random.randint(0, 10) < 10 else '6.0'   # 10% of not updated agent

        device.set_raw(device.to_dict())
        tanium_devices.append(device)

    set_agents_last_seen(tanium_devices)

    return tanium_devices


def create_qualys_from_ad(ad_devices: List[DeviceAdapter]):
    qualys_devices = []
    for i, ad_device in enumerate(ad_devices):
        if i % 5000 == 0:
            print(f'Generated {i} Qualys devices')
        device = create_my_device_adapter('qualys_scans')
        device.name = f'qualys_agent-{ad_device.name}'
        device.hostname = ad_device.hostname.split('.')[0]
        device.id = f'Qualys_Agent_{device.hostname}'
        device._dict['os'] = ad_device._dict['os'].to_dict().copy()
        ad_ip = ad_device.network_interfaces[0].ips[0]
        device.add_nic(ips=[ad_ip])

        device.adapter_properties = [AdapterProperty.Vulnerability_Assessment.name, AdapterProperty.Agent.name]
        device.agent_version = '1.6.4.9' if random.randint(0, 10) < 10 else '1.4.5.232'  # 10% of not updated agent
        device.physical_location = ad_device.ad_site_location

        device.set_raw(device.to_dict())
        qualys_devices.append(device)

    set_agents_last_seen(qualys_devices)
    for device in qualys_devices:
        if device.last_seen + timedelta(days=30) < datetime.now():
            device.agent_status = 'STATUS_INACTIVE'
        else:
            device.agent_status = 'STATUS_ACTIVE'
            if random.randint(0, 9) < 3:
                device.add_qualys_vuln(vuln_id=uuid4(),
                                       last_found=datetime.now() - timedelta(days=random.randint(7, 14)),
                                       qid=uuid4(),
                                       first_found=datetime.now() - timedelta(days=random.randint(14, 21))
                                       )

    return qualys_devices


def main():
    mock_manager = MockManager()
    print('[+] Generating AD devices')
    ad_devices = create_ad_devices()

    print('[+] Generating SCCM devices')
    random.shuffle(ad_devices)  # randomize list to make correlations with other adapters be different all the time
    sccm_devices = create_sccm_from_ad(ad_devices[:NUMBER_OF_DEVICES_SCCM])

    print('[+] Generating EPO devices')
    random.shuffle(ad_devices)  # randomize list to make correlations with other adapters be different all the time
    epo_devices = create_epo_from_ad(ad_devices[:NUMBER_OF_DEVICES_EPO])

    print('[+] Generating Tanium devices')
    random.shuffle(ad_devices)  # randomize list to make correlations with other adapters be different all the time
    tanium_devices = create_tanium_from_ad(ad_devices[:NUMBER_OF_DEVICES_TANIUM])

    print('[+] Generating Qualys devices')
    random.shuffle(ad_devices)  # randomize list to make correlations with other adapters be different all the time
    qualys_devices = create_qualys_from_ad(ad_devices[:NUMBER_OF_DEVICES_QUALYS])

    print('[+] Pushing to DB')
    mock_manager.delete_db()
    mock_manager.put_devices(ad_devices, 'active_directory_adapter')
    mock_manager.put_devices(sccm_devices, 'sccm_adapter')
    mock_manager.put_devices(epo_devices, 'epo_adapter')
    mock_manager.put_devices(tanium_devices, 'tanium_adapter')
    mock_manager.put_devices(qualys_devices, 'qualys_scans_adapter')


if __name__ == '__main__':
    sys.exit(main())
