from axonius.device import SCANNER_FIELD_NAME
from static_correlator_engine import StaticCorrelatorEngine, _correlate_scanner_hostname_ip, _correlate_scanner_mac_ip

import logging
import sys

from axonius.correlator_base import CorrelationResult
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME


correlator_logger = logging.getLogger()
correlator_logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(' [Correlator] %(message)s')
ch.setFormatter(formatter)
correlator_logger.addHandler(ch)


def correlate(devices):
    res = list(StaticCorrelatorEngine(correlator_logger).correlate(devices))
    print(res)
    return res


def run_all():
    test_empty()
    test_no_correlation()
    test_rule1_correlation()
    test_rule1_os_contradiction()


def test_empty():
    assert len(correlate([])) == 0


def test_no_correlation():
    devices = [
        {
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'ad1',
                    PLUGIN_UNIQUE_NAME: 'ad1',
                    'data': {
                        'id': "idad1",
                        'os': {
                            'bitness': 32,
                            'distribution': 'Ubuntu',
                            'type': 'Linux'
                        },
                        'hostname': "ubuntuLolol",  # Capital letter in in purpose
                        'network_interfaces': [{
                            'mac': 'mymac',
                            'ip': [
                                '1.1.1.2'
                            ]
                        }
                        ]
                    }
                }
            ],
        },
        {
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'ad2',
                    PLUGIN_UNIQUE_NAME: 'ad2',
                    'data': {
                        'id': "idad2",
                        'os': {
                            'bitness': 32,
                            'distribution': 'Ubuntu',
                            'type': 'Linux'
                        },
                        'hostname': "ubuntulolol",
                        'network_interfaces': [{
                            'mac': 'mymac',
                            'ip': [
                                '1.1.1.1'
                            ]
                        }
                        ]
                    }
                }
            ]
        },
        {
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'ad3',
                    PLUGIN_UNIQUE_NAME: 'ad3',
                    'data': {
                        'id': "idad3",
                        'os': {
                            'bitness': 32,
                            'distribution': 'Ubuntu',
                            'type': 'NotLinux'
                        },
                        'hostname': "ubuntulolol",
                        'network_interfaces': [{
                            'mac': 'mymac',
                            'ip': [
                                '1.1.1.3'
                            ]
                        }
                        ]
                    }
                }
            ]
        },
        {
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'ad4',
                    PLUGIN_UNIQUE_NAME: 'ad4',
                    'data': {
                        'id': "idad4",
                        'os': {
                            'bitness': 32,
                            'distribution': 'Ubuntu',
                            'type': 'NotLinux'
                        },
                        'hostname': "nothostname",
                        'network_interfaces': [{
                            'mac': 'mymac1',
                            'ip': [
                                '1.1.1.1'
                            ]
                        }
                        ]}
                }
            ]
        }
    ]
    results = correlate(devices)
    assert len(results) == 0


def test_rule1_correlation():
    """
    Test a very simple correlation that should happen
    because IP+HOSTNAME+OS
    :return:
    """
    devices = [
        {
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'ad',
                    PLUGIN_UNIQUE_NAME: 'ad1',
                    'data': {
                        'id': "idad1",
                        'os': {
                            'bitness': 32,
                            'distribution': 'Ubuntu',
                            'type': 'Linux'
                        },
                        'hostname': "ubuntuLolol",  # Capital letter in in purpose
                        'network_interfaces': [{
                            'mac': 'mymac',
                            'ip': [
                                '1.1.1.1'
                            ]
                        }
                        ]}
                }
            ],
        },
        {
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'esx',
                    PLUGIN_UNIQUE_NAME: 'esx1',
                    'data': {
                        'id': "idesx1",
                        'os': {
                            'bitness': 32,
                            'distribution': 'Ubuntu',
                            'type': 'Linux'
                        },
                        'hostname': "ubuntulolol",
                        'network_interfaces': [{
                            'mac': 'mymac',
                            'ip': [
                                '1.1.1.1'
                            ]
                        }
                        ]
                    }
                }
            ]
        }
    ]
    results = correlate(devices)
    assert len(results) == 1

    result = results[0]
    assert isinstance(result, CorrelationResult)
    assert len(result.associated_adapter_devices) == 2
    (first_name, first_id), (second_name, second_id) = result.associated_adapter_devices
    assert (('ad1' == first_name and 'esx1' == second_name) or
            ('ad1' == second_name and 'esx1' == first_name))
    assert (('idad1' == first_id and 'idesx1' == second_id) or
            ('idad1' == second_id and 'idesx1' == first_id))


def test_rule1_os_contradiction():
    """
    Test a very simple correlation that should happen
    because IP+HOSTNAME+OS
    :return:
    """
    devices = [
        {
            'internal_axon_id': 'Mark_you_destroyed_our_life',
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'ad',
                    PLUGIN_UNIQUE_NAME: 'ad1',
                    'data': {
                        'id': "idad1",
                        'os': {
                            'bitness': 32,
                            'distribution': 'Ubuntu',
                            'type': 'Linux'
                        },
                        'hostname': "ubuntuLolol",  # Capital letter in in purpose
                        'network_interfaces': [{
                            'mac': 'mymac',
                            'ip': [
                                '1.1.1.1'
                            ]
                        }
                        ]
                    }
                }
            ],
        },
        {
            'internal_axon_id': 'Mark_you_destroyed_our_life2',
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'esx',
                    PLUGIN_UNIQUE_NAME: 'esx1',
                    'data': {
                        'id': "idesx1",
                        'os': {
                            'bitness': 32,
                            'distribution': 'Ubuntu',
                            'type': 'NotLinux'
                        },
                        'hostname': "ubuntulolol",
                        'network_interfaces': [{
                            'mac': 'mymac',
                            'ip': [
                                '1.1.1.1'
                            ]
                        }
                        ]}
                },
                {
                    'plugin_name': 'aws',
                    PLUGIN_UNIQUE_NAME: 'aws1',
                    'data': {
                        'id': "idaws1",
                        'os': {
                            'bitness': 32,
                            'distribution': 'Ubuntu',
                            'type': 'Linux'
                        },
                        'hostname': "ubuntulolol",
                        'network_interfaces': [{
                            'mac': 'mymac',
                            'ip': [
                                '1.1.1.1'
                            ]
                        }
                        ]
                    }
                }
            ]
        }
    ]
    results = correlate(devices)
    assert len(results) == 0


def test_rule2_correlation():
    """
    Test a very simple correlation that should happen
    because IP+MAC+OS
    :return:
    """
    devices = [
        {
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'ad',
                    PLUGIN_UNIQUE_NAME: 'ad1',
                    'data': {
                        'id': "idad1",
                        'os': {
                            'bitness': 32,
                            'distribution': 'Ubuntu',
                            'type': 'Linux'
                        },
                        'hostname': "ubuntuLolol",  # Capital letter in in purpose
                        'network_interfaces': [{
                            'mac': 'AA-BB-CC-11-22-33',
                            'ip': [
                                '1.1.1.1'
                            ]
                        }
                        ]}
                }
            ],
        },
        {
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'esx',
                    PLUGIN_UNIQUE_NAME: 'esx1',
                    'data': {
                        'id': "idesx1",
                        'os': {
                            'bitness': 32,
                            'distribution': 'Ubuntu',
                            'type': 'Linux'
                        },
                        'network_interfaces': [{
                            'mac': 'AA:bb-CC-11-22-33',
                            'ip': [
                                '1.1.1.1'
                            ]
                        }
                        ]
                    }
                }
            ]
        }
    ]
    results = correlate(devices)
    assert len(results) == 1

    result = results[0]
    assert isinstance(result, CorrelationResult)
    assert len(result.associated_adapter_devices) == 2
    (first_name, first_id), (second_name, second_id) = result.associated_adapter_devices
    assert (('ad1' == first_name and 'esx1' == second_name) or
            ('ad1' == second_name and 'esx1' == first_name))
    assert (('idad1' == first_id and 'idesx1' == second_id) or
            ('idad1' == second_id and 'idesx1' == first_id))


def test_rule1_scanner_correlation():
    """
    Test a very simple correlation that should happen
    because IP+HOSTNAME for scanners
    :return:
    """
    devices = [
        {
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'ad',
                    PLUGIN_UNIQUE_NAME: 'ad1',
                    'data': {
                        'id': "idad1",
                        'os': {
                            'bitness': '',
                            'distribution': '',
                            'type': ''
                        },
                        SCANNER_FIELD_NAME: True,
                        'hostname': "ubuntuLolol",  # Capital letter in in purpose
                        'network_interfaces': [{
                            'ip': [
                                '1.1.1.1'
                            ]
                        }
                        ]}
                }
            ],
        },
        {
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'esx',
                    PLUGIN_UNIQUE_NAME: 'esx1',
                    'data': {
                        'id': "idesx1",
                        'os': {
                            'bitness': 32,
                            'distribution': 'Ubuntu',
                            'type': 'Linux'
                        },
                        'hostname': "ubuntulolol",
                        'network_interfaces': [{
                            'mac': 'aa:bb:cc:dd:ee:ff',
                            'ip': [
                                '1.1.1.1'
                            ]
                        }
                        ]
                    }
                }
            ]
        }
    ]
    results = correlate(devices)
    assert len(results) == 1

    result = results[0]
    assert isinstance(result, CorrelationResult)
    assert len(result.associated_adapter_devices) == 2
    (first_name, first_id), (second_name, second_id) = result.associated_adapter_devices
    assert (('ad1' == first_name and 'esx1' == second_name) or
            ('ad1' == second_name and 'esx1' == first_name))
    assert (('idad1' == first_id and 'idesx1' == second_id) or
            ('idad1' == second_id and 'idesx1' == first_id))
    assert result.reason == 'ScannerAnalysisMacIP'


def test_rule1_scanner_correlation_fails_no_scanner_field():
    """
    Test a very simple correlation that should happen
    because IP+HOSTNAME for scanners
    :return:
    """
    devices = [
        {
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'ad',
                    PLUGIN_UNIQUE_NAME: 'ad1',
                    'data': {
                        'id': "idad1",
                        'os': {
                            'bitness': '',
                            'distribution': '',
                            'type': ''
                        },
                        'hostname': "ubuntuLolol",  # Capital letter in in purpose
                        'network_interfaces': [{
                            'ip': [
                                '1.1.1.1'
                            ]
                        }
                        ]}
                }
            ],
        },
        {
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'esx',
                    PLUGIN_UNIQUE_NAME: 'esx1',
                    'data': {
                        'id': "idesx1",
                        'os': {
                            'bitness': 32,
                            'distribution': 'Ubuntu',
                            'type': 'Linux'
                        },
                        'hostname': "ubuntulolol",
                        'network_interfaces': [{
                            'mac': 'aa:bb:cc:dd:ee:ff',
                            'ip': [
                                '1.1.1.1'
                            ]
                        }
                        ]
                    }
                }
            ]
        }
    ]
    results = correlate(devices)
    assert len(results) == 0


def test_rule2_scanner_correlation():
    """
    Test a very simple correlation that should happen
    because IP+MAC of scanner
    :return:
    """
    devices = [
        {
            "_id": "5a5f850f97a9d80013abdd8f",
            "internal_axon_id": "b197c026e6e44fa89cbeb98cef85369b",
            "accurate_for_datetime": "2018-01-17T17:17:03.845Z",
            "adapters": [
                {
                    "client_used": "10.0.2.119:22",
                    "plugin_type": "Adapter",
                    "plugin_name": "cisco_adapter",
                    "plugin_unique_name": "cisco_adapter_30621",
                    "accurate_for_datetime": "2018-01-17T17:17:03.824Z",
                    "data": {
                        "id": "10.0.2.229",
                        "network_interfaces": [
                            {
                                "ip": [
                                    "10.0.2.229"
                                ],
                                "mac": "06:2D:ED:0F:2D:E4"
                            }
                        ],
                        "raw": {
                            "IP": "10.0.2.229",
                            "Interface": "gigabitethernet1",
                            "MAC": "06:2D:ED:0F:2D:E4"
                        },
                        "scanner": True,
                        "pretty_id": "unknown-orange-woozy-shape"
                    }
                }
            ],
            "tags": []
        },
        {
            "_id": "5a5f851197a9d80013abde06",
            "internal_axon_id": "aaed1dbe31974cf496576741054265b8",
            "accurate_for_datetime": "2018-01-17T17:17:05.137Z",
            "adapters": [
                {
                    "client_used": "puppet",
                    "plugin_type": "Adapter",
                    "plugin_name": "puppet_adapter",
                    "plugin_unique_name": "puppet_adapter_13816",
                    "accurate_for_datetime": "2018-01-17T17:17:05.120Z",
                    "data": {
                        "id": "puppet.axonius.lan",
                        "name": "puppet",
                        "network_interfaces": [
                            {
                                "ip": [
                                    "127.0.0.1",
                                    "::1"
                                ]
                            },
                            {
                                "ip": [
                                    "10.0.2.229",
                                    "fe80::42d:edff:fe0f:2de4"
                                ],
                                "mac": "06:2d:ed:0f:2d:e4"
                            }
                        ],
                        "os": {
                            "bitness": 64,
                            "distribution": "Ubuntu",
                            "major": "16.04",
                            "type": "Linux"
                        },
                        "raw": {
                            "aio_agent_version": "1.10.9",
                            "apt_dist_updates": 27,
                            "apt_has_dist_updates": True,
                            "apt_has_updates": True,
                            "apt_package_dist_updates": [
                                "dpkg",
                                "grub-pc",
                                "grub-pc-bin",
                                "grub2-common",
                                "grub-common",
                                "dnsmasq-base",
                                "lxd",
                                "lxd-client",
                                "lxcfs",
                                "squashfs-tools",
                                "ubuntu-core-launcher",
                                "snapd",
                                "libseccomp2",
                                "distro-info-data",
                                "klibc-utils",
                                "initramfs-tools",
                                "initramfs-tools-core",
                                "initramfs-tools-bin",
                                "libklibc",
                                "libdrm-common",
                                "libdrm2",
                                "postgresql-common",
                                "postgresql-client-common",
                                "puppetlabs-release-pc1",
                                "unattended-upgrades",
                                "cloud-init",
                                "grub-legacy-ec2"
                            ],
                            "apt_package_updates": [
                                "dpkg",
                                "grub-pc",
                                "grub-pc-bin",
                                "grub2-common",
                                "grub-common",
                                "dnsmasq-base",
                                "lxd",
                                "lxd-client",
                                "lxcfs",
                                "squashfs-tools",
                                "ubuntu-core-launcher",
                                "snapd",
                                "libseccomp2",
                                "distro-info-data",
                                "klibc-utils",
                                "initramfs-tools",
                                "initramfs-tools-core",
                                "initramfs-tools-bin",
                                "libklibc",
                                "postgresql-common",
                                "postgresql-client-common",
                                "puppetlabs-release-pc1",
                                "unattended-upgrades",
                                "cloud-init",
                                "grub-legacy-ec2"
                            ],
                            "apt_reboot_required": True,
                            "apt_security_dist_updates": 0,
                            "apt_security_updates": 0,
                            "apt_update_last_success": 1516181412,
                            "apt_updates": 25,
                            "architecture": "amd64",
                            "augeas": {
                                "version": "1.4.0"
                            },
                            "augeasversion": "1.4.0",
                            "bios_release_date": "08/24/2006",
                            "bios_vendor": "Xen",
                            "bios_version": "4.2.amazon",
                            "blockdevice_xvda_size": 21474836480,
                            "blockdevices": "xvda",
                            "cached_catalog_status": None,
                            "catalog_environment": "production",
                            "catalog_timestamp": "2018-01-17T17:16:05.844Z",
                            "certname": "puppet.axonius.lan",
                            "chassistype": "Other",
                            "clientcert": "puppet.axonius.lan",
                            "clientnoop": False,
                            "clientversion": "4.10.9",
                            "deactivated": None,
                            "dhcp_servers": {
                                "eth0": "10.0.2.1",
                                "system": "10.0.2.1"
                            },
                            "disks": {
                                "xvda": {
                                    "size": "20.00 GiB",
                                    "size_bytes": 21474836480
                                }
                            },
                            "dmi": {
                                "bios": {
                                    "release_date": "08/24/2006",
                                    "vendor": "Xen",
                                    "version": "4.2.amazon"
                                },
                                "chassis": {
                                    "type": "Other"
                                },
                                "manufacturer": "Xen",
                                "product": {
                                    "name": "HVM domU",
                                    "serial_number": "ec208733-2e02-c183-dcba-297bb533701b",
                                    "uuid": "EC208733-2E02-C183-DCBA-297BB533701B"
                                }
                            },
                            "domain": "axonius.lan",
                            "ec2_metadata": {
                                "ami-id": "ami-82f4dae7",
                                "ami-launch-index": "0",
                                "ami-manifest-path": "(unknown)",
                                "block-device-mapping": {
                                    "ami": "/dev/sda1",
                                    "root": "/dev/sda1"
                                },
                                "hostname": "ip-10-0-2-229.axonius.local",
                                "instance-action": "none",
                                "instance-id": "i-02fea919b714a0847",
                                "instance-type": "t2.medium",
                                "local-hostname": "ip-10-0-2-229.axonius.local",
                                "local-ipv4": "10.0.2.229",
                                "mac": "06:2d:ed:0f:2d:e4",
                                "metrics": {
                                    "vhostmd": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                                },
                                "network": {
                                    "interfaces": {
                                        "macs": {
                                            "06:2d:ed:0f:2d:e4": {
                                                "device-number": "0",
                                                "interface-id": "eni-77a58022",
                                                "local-hostname": "ip-10-0-2-229.axonius.local",
                                                "local-ipv4s": "10.0.2.229",
                                                "mac": "06:2d:ed:0f:2d:e4",
                                                "owner-id": "405773942477",
                                                "security-group-ids": "sg-8e00dce6",
                                                "security-groups": "default",
                                                "subnet-id": "subnet-843a4cff",
                                                "subnet-ipv4-cidr-block": "10.0.2.0/24",
                                                "vpc-id": "vpc-12290d7b",
                                                "vpc-ipv4-cidr-block": "10.0.0.0/16",
                                                "vpc-ipv4-cidr-blocks": "10.0.0.0/16"
                                            }
                                        }
                                    }
                                },
                                "placement": {
                                    "availability-zone": "us-east-2b"
                                },
                                "profile": "default-hvm",
                                "public-keys": {
                                    "0": {
                                        "openssh-key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC1ibAsH0OMA9Mk3IYaVhRSy6Lg1vuBveBzn+4mtcX3wZK/4nnHpgPM48Sbhw51QF0DhEstJx1BoFHkC3QmgUvskX4JjnmDpumVQuTgAf97Z5hNAiyvdbi3D9t4vradjsdnOnlSHAyctFmtGgA3y7IBUR99qrAwV97zdJQY1EmZEJRWpniF9qX444W+1/aiU/R98c4kGrRj5j3gDXIJGEv3KV0l/PFnbL2Of9/IdScme0oLVghYJ6kANyvnBmpwH9Kvl6q8VumlAE6yuPrKwI5iBVl5IAiEK3Gg32LTbuKsdSOVikWxGX+z0FBa2elKqg5PFjJ6P9ceLxozT4eANhvT office-aws-private-subnet"
                                    }
                                },
                                "reservation-id": "r-0c8f3c14a4cdaf608",
                                "security-groups": "default",
                                "services": {
                                    "domain": "amazonaws.com",
                                    "partition": "aws"
                                }
                            },
                            "expired": None,
                            "facterversion": "3.6.8",
                            "facts_environment": "production",
                            "facts_timestamp": "2018-01-17T17:16:04.085Z",
                            "filesystems": "btrfs,ext2,ext3,ext4,msdos,squashfs,ufs,vfat,xfs",
                            "fqdn": "puppet.axonius.lan",
                            "gid": "root",
                            "hardwareisa": "x86_64",
                            "hardwaremodel": "x86_64",
                            "hostname": "puppet",
                            "id": "root",
                            "identity": {
                                "gid": 0,
                                "group": "root",
                                "privileged": True,
                                "uid": 0,
                                "user": "root"
                            },
                            "interfaces": "eth0,lo",
                            "ip6tables_version": "1.6.0",
                            "ipaddress": "10.0.2.229",
                            "ipaddress6": "fe80::42d:edff:fe0f:2de4",
                            "ipaddress6_eth0": "fe80::42d:edff:fe0f:2de4",
                            "ipaddress6_lo": "::1",
                            "ipaddress_eth0": "10.0.2.229",
                            "ipaddress_lo": "127.0.0.1",
                            "iptables_persistent_version": "1.0.4",
                            "iptables_version": "1.6.0",
                            "is_pe": False,
                            "is_virtual": True,
                            "kernel": "Linux",
                            "kernelmajversion": "4.4",
                            "kernelrelease": "4.4.0-1041-aws",
                            "kernelversion": "4.4.0",
                            "latest_report_corrective_change": None,
                            "latest_report_hash": None,
                            "latest_report_noop": None,
                            "latest_report_noop_pending": None,
                            "latest_report_status": None,
                            "load_averages": {
                                "15m": 0.0,
                                "1m": 0.0,
                                "5m": 0.0
                            },
                            "lsbdistcodename": "xenial",
                            "lsbdistdescription": "Ubuntu 16.04.3 LTS",
                            "lsbdistid": "Ubuntu",
                            "lsbdistrelease": "16.04",
                            "lsbmajdistrelease": "16.04",
                            "macaddress": "06:2d:ed:0f:2d:e4",
                            "macaddress_eth0": "06:2d:ed:0f:2d:e4",
                            "manufacturer": "Xen",
                            "memory": {
                                "system": {
                                    "available": "1.34 GiB",
                                    "available_bytes": 1435897856,
                                    "capacity": "65.34%",
                                    "total": "3.86 GiB",
                                    "total_bytes": 4142284800,
                                    "used": "2.52 GiB",
                                    "used_bytes": 2706386944
                                }
                            },
                            "memoryfree": "1.34 GiB",
                            "memoryfree_mb": 1369.37890625,
                            "memorysize": "3.86 GiB",
                            "memorysize_mb": 3950.390625,
                            "mountpoints": {
                                "/": {
                                    "available": "17.21 GiB",
                                    "available_bytes": 18480381952,
                                    "capacity": "10.94%",
                                    "device": "/dev/xvda1",
                                    "filesystem": "ext4",
                                    "options": [
                                        "rw",
                                        "relatime",
                                        "discard",
                                        "data=ordered"
                                    ],
                                    "size": "19.32 GiB",
                                    "size_bytes": 20749852672,
                                    "used": "2.11 GiB",
                                    "used_bytes": 2269470720
                                },
                                "/dev/shm": {
                                    "available": "1.93 GiB",
                                    "available_bytes": 2071138304,
                                    "capacity": "0.00%",
                                    "device": "tmpfs",
                                    "filesystem": "tmpfs",
                                    "options": [
                                        "rw",
                                        "nosuid",
                                        "nodev"
                                    ],
                                    "size": "1.93 GiB",
                                    "size_bytes": 2071142400,
                                    "used": "4.00 KiB",
                                    "used_bytes": 4096
                                },
                                "/run": {
                                    "available": "364.73 MiB",
                                    "available_bytes": 382447616,
                                    "capacity": "7.67%",
                                    "device": "tmpfs",
                                    "filesystem": "tmpfs",
                                    "options": [
                                        "rw",
                                        "nosuid",
                                        "noexec",
                                        "relatime",
                                        "size=404520k",
                                        "mode=755"
                                    ],
                                    "size": "395.04 MiB",
                                    "size_bytes": 414228480,
                                    "used": "30.31 MiB",
                                    "used_bytes": 31780864
                                },
                                "/run/lock": {
                                    "available": "5.00 MiB",
                                    "available_bytes": 5242880,
                                    "capacity": "0%",
                                    "device": "tmpfs",
                                    "filesystem": "tmpfs",
                                    "options": [
                                        "rw",
                                        "nosuid",
                                        "nodev",
                                        "noexec",
                                        "relatime",
                                        "size=5120k"
                                    ],
                                    "size": "5.00 MiB",
                                    "size_bytes": 5242880,
                                    "used": "0 bytes",
                                    "used_bytes": 0
                                },
                                "/run/user/1000": {
                                    "available": "395.04 MiB",
                                    "available_bytes": 414228480,
                                    "capacity": "0%",
                                    "device": "tmpfs",
                                    "filesystem": "tmpfs",
                                    "options": [
                                        "rw",
                                        "nosuid",
                                        "nodev",
                                        "relatime",
                                        "size=404520k",
                                        "mode=700",
                                        "uid=1000",
                                        "gid=1000"
                                    ],
                                    "size": "395.04 MiB",
                                    "size_bytes": 414228480,
                                    "used": "0 bytes",
                                    "used_bytes": 0
                                },
                                "/sys/fs/cgroup": {
                                    "available": "1.93 GiB",
                                    "available_bytes": 2071142400,
                                    "capacity": "0%",
                                    "device": "tmpfs",
                                    "filesystem": "tmpfs",
                                    "options": [
                                        "ro",
                                        "nosuid",
                                        "nodev",
                                        "noexec",
                                        "mode=755"
                                    ],
                                    "size": "1.93 GiB",
                                    "size_bytes": 2071142400,
                                    "used": "0 bytes",
                                    "used_bytes": 0
                                }
                            },
                            "mtu_eth0": 9001,
                            "mtu_lo": 65536,
                            "netmask": "255.255.255.0",
                            "netmask6": "ffff:ffff:ffff:ffff::",
                            "netmask6_eth0": "ffff:ffff:ffff:ffff::",
                            "netmask6_lo": "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
                            "netmask_eth0": "255.255.255.0",
                            "netmask_lo": "255.0.0.0",
                            "network": "10.0.2.0",
                            "network6": "fe80::",
                            "network6_eth0": "fe80::",
                            "network6_lo": "::1",
                            "network_eth0": "10.0.2.0",
                            "network_lo": "127.0.0.0",
                            "networking": {
                                "dhcp": "10.0.2.1",
                                "domain": "axonius.lan",
                                "fqdn": "puppet.axonius.lan",
                                "hostname": "puppet",
                                "interfaces": {
                                    "eth0": {
                                        "bindings": [
                                            {
                                                "address": "10.0.2.229",
                                                "netmask": "255.255.255.0",
                                                "network": "10.0.2.0"
                                            }
                                        ],
                                        "bindings6": [
                                            {
                                                "address": "fe80::42d:edff:fe0f:2de4",
                                                "netmask": "ffff:ffff:ffff:ffff::",
                                                "network": "fe80::"
                                            }
                                        ],
                                        "dhcp": "10.0.2.1",
                                        "ip": "10.0.2.229",
                                        "ip6": "fe80::42d:edff:fe0f:2de4",
                                        "mac": "06:2d:ed:0f:2d:e4",
                                        "mtu": 9001,
                                        "netmask": "255.255.255.0",
                                        "netmask6": "ffff:ffff:ffff:ffff::",
                                        "network": "10.0.2.0",
                                        "network6": "fe80::"
                                    },
                                    "lo": {
                                        "bindings": [
                                            {
                                                "address": "127.0.0.1",
                                                "netmask": "255.0.0.0",
                                                "network": "127.0.0.0"
                                            }
                                        ],
                                        "bindings6": [
                                            {
                                                "address": "::1",
                                                "netmask": "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
                                                "network": "::1"
                                            }
                                        ],
                                        "ip": "127.0.0.1",
                                        "ip6": "::1",
                                        "mtu": 65536,
                                        "netmask": "255.0.0.0",
                                        "netmask6": "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
                                        "network": "127.0.0.0",
                                        "network6": "::1"
                                    }
                                },
                                "ip": "10.0.2.229",
                                "ip6": "fe80::42d:edff:fe0f:2de4",
                                "mac": "06:2d:ed:0f:2d:e4",
                                "mtu": 9001,
                                "netmask": "255.255.255.0",
                                "netmask6": "ffff:ffff:ffff:ffff::",
                                "network": "10.0.2.0",
                                "network6": "fe80::",
                                "primary": "eth0"
                            },
                            "operatingsystem": "Ubuntu",
                            "operatingsystemmajrelease": "16.04",
                            "operatingsystemrelease": "16.04",
                            "os": {
                                "architecture": "amd64",
                                "distro": {
                                    "codename": "xenial",
                                    "description": "Ubuntu 16.04.3 LTS",
                                    "id": "Ubuntu",
                                    "release": {
                                        "full": "16.04",
                                        "major": "16.04"
                                    }
                                },
                                "family": "Debian",
                                "hardware": "x86_64",
                                "name": "Ubuntu",
                                "release": {
                                    "full": "16.04",
                                    "major": "16.04"
                                },
                                "selinux": {
                                    "enabled": False
                                }
                            },
                            "osfamily": "Debian",
                            "package_provider": "apt",
                            "partitions": {
                                "/dev/xvda1": {
                                    "filesystem": "ext4",
                                    "label": "cloudimg-rootfs",
                                    "mount": "/",
                                    "partuuid": "35560eaf-01",
                                    "size": "20.00 GiB",
                                    "size_bytes": 2147377100,
                                    "uuid": "512611f4-b05a-4d8a-b743-438b71c5385d"
                                }
                            },
                            "path": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                            "physicalprocessorcount": 1,
                            "processor0": "Intel(R) Xeon(R) CPU E5-2676 v3 @ 2.40GHz",
                            "processor1": "Intel(R) Xeon(R) CPU E5-2676 v3 @ 2.40GHz",
                            "processorcount": 2,
                            "processors": {
                                "count": 2,
                                "isa": "x86_64",
                                "models": [
                                    "Intel(R) Xeon(R) CPU E5-2676 v3 @ 2.40GHz",
                                    "Intel(R) Xeon(R) CPU E5-2676 v3 @ 2.40GHz"
                                ],
                                "physicalcount": 1
                            },
                            "productname": "HVM domU",
                            "puppet_environmentpath": "/etc/puppetlabs/code/environments",
                            "puppet_server": "puppet",
                            "puppet_vardir": "/opt/puppetlabs/puppet/cache",
                            "puppetversion": "4.10.9",
                            "report_environment": None,
                            "report_timestamp": None,
                            "root_home": "/root",
                            "ruby": {
                                "platform": "x86_64-linux",
                                "sitedir": "/opt/puppetlabs/puppet/lib/ruby/site_ruby/2.1.0",
                                "version": "2.1.9"
                            },
                            "rubyplatform": "x86_64-linux",
                            "rubysitedir": "/opt/puppetlabs/puppet/lib/ruby/site_ruby/2.1.0",
                            "rubyversion": "2.1.9",
                            "selinux": False,
                            "serialnumber": "ec208733-2e02-c183-dcba-297bb533701b",
                            "service_provider": "systemd",
                            "ssh": {
                                "dsa": {
                                    "fingerprints": {
                                        "sha1": "SSHFP 2 1 5ad721d844cba208b490b43dde7d647a2f2988ee",
                                        "sha256": "SSHFP 2 2 2e24717bcd11d39db74e37299a987e45151ed6dbb04df566f36cd446aeedc693"
                                    },
                                    "key": "AAAAB3NzaC1kc3MAAACBANeIoDbTtV+wCjwOkl+FHXWkWN2YjCZP5ACVhhLrtPFzDRAm5nGC8Urbqv+vKzibeqphMhKUwmV5S3WOmJEfzqZEqb2HAXA7E793eWVJYq2LTylQ4afpXS5gzjBnAgL6PnzY1XNGfjjFUz1ZqJlvtKXwrP17vioDbadHINLbO44VAAAAFQDbfomtNCI0Rhrri71uxKLbZmfiewAAAIEA1mXgqxkBuChBlbGSTMJtIxXym7aeJL2U1xbuXUqjzvKR3yDT/XE0fg1UT8M1GDzBZxkXy7UsHaMjfsa088hhA92wnm1GG6noj3xK5jJl+QhH73e7WlH0JZAYxQGVSJaHlS903GQsB0/NZhtVMGWU/dJA20vj4XvHkrbnHF3V2QkAAACADxk9m3iKf7kTWjCDoiddTZhvTEG/bhDTZKWAkrIK7oW+BLmVxq5xlOW4r02w6Ug44bS8BEpr1MbccbbVCk5rdJNxg6P7bvE7lB37neBos7IiiC12o6R43LwzuSR8fOF0s+koZ9VKwNOmZ9P7CtWPnTT5txKS40KIb3UoImWOmks="
                                },
                                "ecdsa": {
                                    "fingerprints": {
                                        "sha1": "SSHFP 3 1 befbb24d4175de4fc2f3b7da2f06dacb0643704a",
                                        "sha256": "SSHFP 3 2 c9d49fdb3a93934b949ff0d0e894211e9d75b49b51bd76bcc5e5afc12689f4cb"
                                    },
                                    "key": "AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBBklGjSS9wRe+UAFPyYXoVN37wikohHHTGeGGY8TcGrQWuJ3V25R3EAQ61Tusx3n17YJJfLFk8QOakXUV9xjGLs="
                                },
                                "ed25519": {
                                    "fingerprints": {
                                        "sha1": "SSHFP 4 1 b9b9aeb601a90ab2dbcba0f101171dea71049da2",
                                        "sha256": "SSHFP 4 2 49819b464c3b022e288c32a7404b4b68e2ca650182dd7f9c1f9ecff8e92575cb"
                                    },
                                    "key": "AAAAC3NzaC1lZDI1NTE5AAAAIO9SJG0WZQTqKH5ZGSQ+MARZiLz4e4P5l5AQFJuATAvF"
                                },
                                "rsa": {
                                    "fingerprints": {
                                        "sha1": "SSHFP 1 1 ec9f33a2cb50d57e84f550e90f8dc3de4a5b2d4e",
                                        "sha256": "SSHFP 1 2 e766071b1ca9c6fa3eebd4d8b067cd5c52ba0d807c98f3f40d1c31220600bab1"
                                    },
                                    "key": "AAAAB3NzaC1yc2EAAAADAQABAAABAQDUZG+AKZ+QxF1v9N7MwUMep3J+k8ZJ7CGtmhKujE0nEVswLt1hqbrP9RNSokwUtdDII0epmcY2RRQOWuj7qoEayWKZczgwJhnVn/MGceDw1EA6oEPIWiWUggkf74mpK/Zujj5Wl2uhfhFhHtd7b3vETvCjzJbg3HjX4zxUCVPZUuLhiLncpz+vQuEDth9G4j0PHL6DsAPUMQVyYYngMlHCMdysg6WBq1ZKl/pr0cmb4KX6of7lHi9ZalS4vNssyfAfGHBP9aZbg4mvbcUS2jdNf8eL3G9DrAYZHmFVl+7ilohc4TW+2A5YWhzu/E7PZz3LfBn/DZogjPUwJeM4FZ8B"
                                }
                            },
                            "sshdsakey": "AAAAB3NzaC1kc3MAAACBANeIoDbTtV+wCjwOkl+FHXWkWN2YjCZP5ACVhhLrtPFzDRAm5nGC8Urbqv+vKzibeqphMhKUwmV5S3WOmJEfzqZEqb2HAXA7E793eWVJYq2LTylQ4afpXS5gzjBnAgL6PnzY1XNGfjjFUz1ZqJlvtKXwrP17vioDbadHINLbO44VAAAAFQDbfomtNCI0Rhrri71uxKLbZmfiewAAAIEA1mXgqxkBuChBlbGSTMJtIxXym7aeJL2U1xbuXUqjzvKR3yDT/XE0fg1UT8M1GDzBZxkXy7UsHaMjfsa088hhA92wnm1GG6noj3xK5jJl+QhH73e7WlH0JZAYxQGVSJaHlS903GQsB0/NZhtVMGWU/dJA20vj4XvHkrbnHF3V2QkAAACADxk9m3iKf7kTWjCDoiddTZhvTEG/bhDTZKWAkrIK7oW+BLmVxq5xlOW4r02w6Ug44bS8BEpr1MbccbbVCk5rdJNxg6P7bvE7lB37neBos7IiiC12o6R43LwzuSR8fOF0s+koZ9VKwNOmZ9P7CtWPnTT5txKS40KIb3UoImWOmks=",
                            "sshecdsakey": "AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBBklGjSS9wRe+UAFPyYXoVN37wikohHHTGeGGY8TcGrQWuJ3V25R3EAQ61Tusx3n17YJJfLFk8QOakXUV9xjGLs=",
                            "sshed25519key": "AAAAC3NzaC1lZDI1NTE5AAAAIO9SJG0WZQTqKH5ZGSQ+MARZiLz4e4P5l5AQFJuATAvF",
                            "sshfp_dsa": "SSHFP 2 1 5ad721d844cba208b490b43dde7d647a2f2988ee\nSSHFP 2 2 2e24717bcd11d39db74e37299a987e45151ed6dbb04df566f36cd446aeedc693",
                            "sshfp_ecdsa": "SSHFP 3 1 befbb24d4175de4fc2f3b7da2f06dacb0643704a\nSSHFP 3 2 c9d49fdb3a93934b949ff0d0e894211e9d75b49b51bd76bcc5e5afc12689f4cb",
                            "sshfp_ed25519": "SSHFP 4 1 b9b9aeb601a90ab2dbcba0f101171dea71049da2\nSSHFP 4 2 49819b464c3b022e288c32a7404b4b68e2ca650182dd7f9c1f9ecff8e92575cb",
                            "sshfp_rsa": "SSHFP 1 1 ec9f33a2cb50d57e84f550e90f8dc3de4a5b2d4e\nSSHFP 1 2 e766071b1ca9c6fa3eebd4d8b067cd5c52ba0d807c98f3f40d1c31220600bab1",
                            "sshrsakey": "AAAAB3NzaC1yc2EAAAADAQABAAABAQDUZG+AKZ+QxF1v9N7MwUMep3J+k8ZJ7CGtmhKujE0nEVswLt1hqbrP9RNSokwUtdDII0epmcY2RRQOWuj7qoEayWKZczgwJhnVn/MGceDw1EA6oEPIWiWUggkf74mpK/Zujj5Wl2uhfhFhHtd7b3vETvCjzJbg3HjX4zxUCVPZUuLhiLncpz+vQuEDth9G4j0PHL6DsAPUMQVyYYngMlHCMdysg6WBq1ZKl/pr0cmb4KX6of7lHi9ZalS4vNssyfAfGHBP9aZbg4mvbcUS2jdNf8eL3G9DrAYZHmFVl+7ilohc4TW+2A5YWhzu/E7PZz3LfBn/DZogjPUwJeM4FZ8B",
                            "system_uptime": {
                                "days": 15,
                                "hours": 378,
                                "seconds": 1362928,
                                "uptime": "15 days"
                            },
                            "timezone": "UTC",
                            "trusted": {
                                "authenticated": "remote",
                                "certname": "puppet.axonius.lan",
                                "domain": "axonius.lan",
                                "extensions": {},
                                "hostname": "puppet"
                            },
                            "uptime": "15 days",
                            "uptime_days": 15,
                            "uptime_hours": 378,
                            "uptime_seconds": 1362928,
                            "uuid": "EC208733-2E02-C183-DCBA-297BB533701B",
                            "virtual": "xenhvm"
                        },
                        "pretty_id": "goofy-better-charming-long"
                    }
                }
            ],
            "tags": []
        }
    ]
    results = correlate(devices)
    assert len(results) == 1

    result = results[0]
    assert isinstance(result, CorrelationResult)
    assert len(result.associated_adapter_devices) == 2
    (first_name, first_id), (second_name, second_id) = result.associated_adapter_devices
    assert (('cisco_adapter_30621' == first_name and 'puppet_adapter_13816' == second_name) or
            ('puppet_adapter_13816' == second_name and 'cisco_adapter_30621' == first_name))
    assert (('puppet.axonius.lan' == first_id and '10.0.2.229' == second_id) or
            ('10.0.2.229' == first_id and 'puppet.axonius.lan' == second_id))
    assert result.reason == 'ScannerAnalysisMacIP'


def test_rule2_scanner_correlation_fails_no_scanner_field():
    """
    Test a very simple correlation that should happen
    because IP+MAC of scanner
    :return:
    """
    devices = [
        {
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'ad',
                    PLUGIN_UNIQUE_NAME: 'ad1',
                    'data': {
                        'id': "idad1",
                        'os': {
                            'bitness': '',
                            'distribution': '',
                            'type': ''
                        },
                        'hostname': "",
                        'network_interfaces': [{
                            'mac': 'AA-BB-CC-11-22-33',
                            'ip': [
                                '1.1.1.1'
                            ]
                        }
                        ]}
                }
            ],
        },
        {
            'tags': [],
            'adapters': [
                {
                    'plugin_name': 'esx',
                    PLUGIN_UNIQUE_NAME: 'esx1',
                    'data': {
                        'id': "idesx1",
                        'os': {
                            'bitness': 32,
                            'distribution': 'Ubuntu',
                            'type': 'Linux'
                        },
                        'hostname': "asfasfsaf",
                        'network_interfaces': [{
                            'mac': 'AA:bb-CC-11-22-33',
                            'ip': [
                                '1.1.1.1'
                            ]
                        }
                        ]
                    }
                }
            ]
        }
    ]
    results = correlate(devices)
    for result in results:
        assert result.reason != 'ScannerAnalysisMacIP'


if __name__ == '__main__':
    import pytest
    pytest.main(["."])
