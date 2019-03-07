"""
ParsingUtils.py: Collection of utils that might be used by parsers, specifically adapters
"""
import base64
import binascii
import csv
import datetime
import ipaddress
import logging
import os
import re
import string
import sys
from types import FunctionType
from typing import Callable, NewType, List

import dateutil.parser
import pytz

import axonius
from axonius.entities import EntityType
from axonius.utils.datetime import is_date_real, parse_date

logger = logging.getLogger(f'axonius.{__name__}')

osx_version_fallback = re.compile(r'[^\w](\d+\.\d+.\d+)')
osx_version = re.compile(r'[^\w](\d+\.\d+.\d+)[^\w]')
osx_version_full = re.compile(r'[^\w](\d+\.\d+.\d+)\s*(\(\w+\))')
# match any of: (Ubuntu / ubuntu / UbuntuServer / ubuntuserver / Ubuntuserver) + version number
ubuntu_full = re.compile(r'([Uu]buntu(?:[Ss]erver)? \d\d\.\d\d(?:\.\d+)?)')
mobile_version = re.compile(r'(\d+\.\d+.\d+)')

# Unfortunately there's no normalized way to return a hostname - currently many adapters return hostname.domain.
# However in non-windows systems, the hostname itself can contain "." which means there's no way to tell which part is
# the hostname when splitting.
# The problem starts as some adapters yield a hostname with a default domain added to it even when a domain exists, and
# some don't return a domain at all.
# In order to ignore that and allow proper hostname comparison we want to remove the default domains.
# Currently (28/01/2018) this means removing LOCAL and WORKGROUP.
# Also we want to split the hostname on "." and make sure one split list is the beginning of the other.
NORMALIZED_HOSTNAME = 'normalized_hostname'
OSX_NAMES = ['mojave', 'sierra', 'capitan', 'yosemite', 'mavericks', 'darwin']
# In some cases we don't want to use compare_hostnames because indexing using it is complicated
# and in some cases indexsing is performance critical
NORMALIZED_HOSTNAME_STRING = 'normalized_hostname_string'
NET_BIOS_MAX_LENGTH = 15
DEFAULT_DOMAIN_EXTENSIONS = ['.LOCAL', '.WORKGROUP', '.LOCALHOST']
# In MacOs hostname of the same computer can return in different shapes,
# that's why we would like to compare them without these strings
DEFAULT_MAC_EXTENSIONS = ['-MACBOOK-PRO', 'MACBOOK-PRO', '-MBP', 'MBP', '-MBA', '-MACBOOK-AIR', 'MACBOOK-AIR'] + \
                         [f"-MBP-{index}" for index in range(20)] + [f"-MBP-0{index}" for index in range(10)] + ['-AIR',
                                                                                                                 'AIR'] + \
                         [f"-MACBOOK-PRO-{index}" for index in range(20)] + \
                         [f"-MACBOOK-PRO-0{index}" for index in range(10)] + \
                         [f"MACBOOKPRO{index}" for index in range(20)] + [f"MACBOOKPRO0{index}" for index in range(10)]
# NORMALIZED_IPS/MACS fields will hold the set of IPs and MACs an adapter devices has extracted.
# Without it, in order to compare IPs and MACs we would have to go through the list of network interfaces and extract
# them each time.
NORMALIZED_IPS = 'normalized_ips'
NORMALIZED_MACS = 'normalized_macs'
ALLOWED_VAR_CHARACTERS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'

# This number stands for the default number of days needed for us to say a device is old,
# first use if for correlation at is_old_device
DEFAULT_NUMBER_OF_DAYS_FOR_OLD_DEVICE = 7

TO_REMOVE_VALUE = object()

pair_comparator = NewType('pair_comparator', FunctionType)
parameter_function = NewType('parameter_function', Callable)

oui_data = open(os.path.join(axonius.__path__[0], 'oui.csv'), encoding='utf8').read()

# dict: MAC 3 first bytes to manufacturer data
mac_manufacturer_details = {x[1]: x for x in
                            csv.DictReader(oui_data.splitlines(), csv.Sniffer().sniff(oui_data[:1024])).reader}
del oui_data


def parse_bool_from_raw(bool_raw_value, raise_on_exception=False):
    """
    Gets a raw value and returns the bool from it. we do it since bool(x) isn't good enough,
    e.g. bool("false") is True.
    :param bool_raw_value: the raw value
    :param raise_on_exception: (optional) raise an exception if you can't succeed. otherwise return None
    :return:
    """
    # All of the below can happen
    if type(bool_raw_value) == bool:
        return bool_raw_value
    elif type(bool_raw_value) == int:
        return bool(bool_raw_value)
    elif type(bool_raw_value) == str and bool_raw_value.lower() in ["true", "false", "0", "1"]:
        return bool_raw_value.lower() in ["true", "1"]

    if raise_on_exception is True:
        raise ValueError(f"{bool_raw_value} isn't a boolean value")

    else:
        return None


def get_manufacturer_from_mac(mac: str) -> str:
    if mac:
        mac = format_mac(mac).replace(':', '')[:6]
        manufacturer = mac_manufacturer_details.get(mac)
        if manufacturer is None:
            return None
        return f"{manufacturer[2]} ({manufacturer[3]})"


def normalize_var_name(name):
    """
    Takes a string and returns another string which can be a variable name in python.
    :param name:
    :return:
    """
    name = name.replace('-', '_').replace(' ', '_')
    name = ''.join([character for character in name if character in ALLOWED_VAR_CHARACTERS])
    return name


def get_exception_string():
    """
    when inside a catch exception flow, returns a really informative string representing it.
    :return: a string representing the exception.
    """
    exc_type, exc_obj, exc_tb = sys.exc_info()

    ex_str = "Traceback (most recent call last):\n"
    while exc_tb is not None:
        ex_str = ex_str + "  File {0}, line {1}, in {2}\n".format(
            exc_tb.tb_frame.f_code.co_filename,
            exc_tb.tb_lineno,
            exc_tb.tb_frame.f_code.co_name)

        exc_tb = exc_tb.tb_next

    ex_str = ex_str + f"{exc_type}:{exc_obj}"
    return ex_str


def figure_out_cloud(s):
    """
    Figures out a cloud provider. If we can't find it, returns None.
    :param s: the cloud provider, e.g. "amazon-web-services"
    :return: a generic value representing the cloud provider, which you can use for device.cloud_provider
    """
    if not s:
        return None

    cloud_provider = s.lower()

    if "aws" in cloud_provider or "amazon" in cloud_provider:
        return "AWS"
    elif "azure" in cloud_provider or "microsoft" in cloud_provider:
        return "Azure"
    elif "google" in cloud_provider or "gcp" in cloud_provider:
        return "GCP"
    elif "softlayer" in cloud_provider or "ibm" in cloud_provider:
        return "Softlayer"
    elif "vmware" in cloud_provider or "vcenter" in cloud_provider \
            or "vsphere" in cloud_provider or "esx" in cloud_provider:
        return "VMWare"
    elif "alibaba" in cloud_provider or "aliyun" in cloud_provider:
        return "Alibaba"
    elif "oracle" in cloud_provider:
        return "Oracle"
    else:
        return None


def figure_out_os(s):
    """
    Gives something like this
    {
         "type": "Windows",
         "distribution": "Vista",
         "edition": "Home Basic",
         "major": "6.0",
         "minor": "6002",
         "bitness": 32
     },

     (not everything is implemented)
    from stuff like this:
    "Canonical, Ubuntu, 16.04 LTS, amd64 xenial image build on 2017-07-21"
    "Microsoft Windows Server 2016 (64-bit)"
    :param s: description of OS
    :return: dict
    """
    if s is None:
        # this means we don't know anything
        return {}
    orig_s = s
    s = s.strip().lower().replace('®', '')

    makes_64bit = ['amd64', '64-bit', 'x64', '64 bit', 'x86_64', 'Win64']
    makes_32bit = ['32-bit', 'x86']

    bitness = None
    if any(x in s for x in makes_64bit):
        bitness = 64
    elif any(x in s for x in makes_32bit):
        bitness = 32

    os_type = None
    distribution = None
    linux_names = ["linux", 'ubuntu', 'canonical', 'red hat',
                   'debian', 'fedora', 'centos', 'oracle', 'opensuse', 'rhel server', 'sles']

    ios_devices = ["iphone", "ipad", "apple"]
    ios_names = ios_devices + ["ios"]

    # Start with the one who have for sure capital in their names
    # The first part is not enough, since some devices have only 'IOS' in them, but not "cisco".
    # We have seen this happening in clients (a device with 2 adapters had "Cisco", "iOS" operating systems,
    # in a client that did not let us connect to any system that see mobile devices)
    if 'cisco' in s or ('IOS' in orig_s and not any(x in s for x in ios_devices)):
        # If it has 'cisco', or it has 'IOS' (upper letters) and it doesn't have 'iphone', 'ipad', etc.
        os_type = 'Cisco'
    elif 'windows' in s or ('win' in s and 'darwin' not in s):
        os_type = 'Windows'
        # XP must reamin the last item in the list because there is a chance it will be found in "s" by chacne
        windows_distribution = ['Vista', 'Windows 7', 'Windows 8', 'Windows 8.1', 'Windows 10',
                                'Windows Server 2003', 'Win10', 'Win7', 'Win8', 'Windows 2016',
                                'Windows 2008', 'Windows 2012', 'Windows 2000',
                                'Windows Server 2008', 'Windows Server 2012', 'Windows Server 2016', 'XP',
                                'WindowsServer 2003', 'WindowsServer 2008', 'WindowsServer 2012', 'WindowsServer 2016']
        for dist in windows_distribution:
            if dist.lower() in s:
                distribution = dist.replace("Windows ", "").replace("Windows", "").replace("Win", "")
                break
    elif 'android' in s:
        os_type = 'Android'
        version = mobile_version.findall(s)
        if len(version):
            distribution = version[0]
    elif any(x in s for x in linux_names):
        os_type = 'Linux'
        linux_distributions = [ubuntu_full, "Ubuntu", "Red Hat", "Debian", "Fedora", 'RHEL']
        for dist in linux_distributions:
            if isinstance(dist, str):
                if dist.lower() in s:
                    distribution = dist
                    break
            else:
                found_values = dist.findall(orig_s)
                if found_values:
                    assert isinstance(found_values[0], str)
                    distribution = found_values[0]
                    break
    elif ('os x' in s) or ('osx' in s) or ('macos' in s) or ('mac os' in s) \
            or any(elem in s for elem in OSX_NAMES):
        os_type = 'OS X'
        version = osx_version_full.findall(s)
        if len(version) > 0:
            distribution = ' '.join(version[0])
        else:
            version = osx_version.findall(s)
            if len(version) > 0:
                distribution = version[0]
            else:
                version = osx_version_fallback.findall(s)
                if len(version) > 0:
                    distribution = version[0]
    elif any(x in s for x in ios_names):
        os_type = 'iOS'
        version = mobile_version.findall(s)
        if len(version):
            distribution = version[0]
    elif 'freebsd' in s:
        os_type = "FreeBSD"
        distribution = "FreeBSD"
    elif 'junos' in s:
        os_type = "FreeBSD"
        distribution = "Junos OS"
    elif s.startswith('vmware'):
        os_type = "VMWare"
        esx_distributions = ['ESX 4.0',
                             'ESX 4.1',
                             'ESXi 4.0',
                             'ESXi 4.1',
                             'ESXi 5.0',
                             'ESXi 5.1',
                             'ESXi 5.1.0',
                             'ESXi 5.1.0a',
                             'ESXi 5.5',
                             'ESXi 6.0',
                             'ESXi 6.0.0b',
                             'ESXi 6.5',
                             'ESXi 6.5.',
                             'ESXi 6.5.0',
                             'ESXi 6.5.0d',
                             'ESXi/ESX 4.1']
        distribution = s.replace("VMWare ", "")
        if distribution not in esx_distributions:
            distribution = "(?) " + distribution
    elif 'mikrotik' in s.lower():
        os_type = 'Mikrotik'

    return {"type": os_type,
            "distribution": distribution,
            "bitness": bitness}


def convert_ldap_searchpath_to_domain_name(ldap_search_path):
    """
    Converts LDAP search path to DC.
    e.g. 'CN=DESKTOP-MPP10U1,CN=Computers,DC=TestDomain,DC=test' -> "TestDomain.test"
    :param ldap_search_path: the str
    :return:
    """

    return ".".join([x[3:] for x in ldap_search_path.strip().split(",") if x.lower().startswith("dc=")])


def get_organizational_units_from_dn(distinguished_name):
    try:
        return [ou[3:] for ou in distinguished_name.split(",") if ou.startswith("OU=")]
    except Exception:
        return None


def is_domain_valid(domain):
    """
    :param doomain: e.g. TestDomain
    :return: e.g. Whether domain exist and has a valid value which is not a local value
    """
    domain = (domain or '').strip().lower()
    if domain and not 'workgroup' in domain and not 'local' in domain and \
            not 'n/a' in domain:
        return True
    return False


def not_aruba_adapters(adapter_device1, adapter_device2):
    if 'aruba' not in adapter_device1.get('plugin_name').lower() and \
            'aruba' not in adapter_device2.get('plugin_name').lower():
        return True
    return False


def get_first_object_from_dn(dn):
    """
    :param dn: e.g. CN=Administrator,CN=Users,DC=TestDomain,DC=test
    :return: e.g. Administrator
    """
    if type(dn) == str:
        dn = dn.replace('\\,', '')
        dn = dn.split(",")
        if len(dn) > 0:
            # This usually looks like CN=User Name, CN=Users, DC=.... so lets take the first one
            rv = dn[0].split("=")
            if len(rv) == 2:
                return rv[1]

    return None


def get_member_of_list_from_memberof(member_of) -> List[str]:
    try:
        if member_of is not None:
            # member_of is a list of dn's that look like "CN=d,OU=b,DC=c,DC=a"
            # so we take each string in the list and transform it to d.b.c.a
            return [".".join([x[3:] for x in member_of_entry.strip().split(",")]) for member_of_entry in member_of]
    except Exception:
        pass

    return None


def is_valid_ip(ip):
    try:
        ipaddress.ip_address(ip)
        return True
    except Exception:
        return False


def format_mac(mac: str):
    if mac is None or mac == '':
        return None
    mac = re.sub('[.:-]', '', mac).lower()  # remove delimiters and convert to lower case
    mac = ''.join(mac.split())  # remove whitespaces

    if len(mac) != 12 or any(map(lambda char: char not in string.hexdigits, mac)):
        raise ValueError(f'Invalid mac {mac}')

    # convert mac in canonical form (eg. 00:80:41:ae:fd:7e)
    mac = ":".join(["%s" % (mac[i:i + 2]) for i in range(0, 12, 2)])
    return mac.upper()


def format_ip(value):
    try:
        return str(ipaddress.ip_address(value))
    except Exception:
        raise ValueError(f'Invalid IP address: {value}')


def format_subnet(value):
    # Must pass {ip}/{int/ipv4_subnet_mask} such that it will be possible to distinguish between two
    # subnet masks (and two ips) on same interface
    try:
        assert '/' in value
        return str(ipaddress.ip_network(value, False))
    except Exception:
        raise ValueError(f'Invalid subnet: {value}')


def ad_integer8_to_timedelta(i8):
    """
    The syntax is Integer8, also called LargeInteger. The value is a 64-bit integer representing time intervals
    in 100-nanosecond ticks.  The value is always negative. For example, if the maximum password age in the domain
    is 10 days, then maxPwdAge will have the value:
    maxPwdAge = (-1) x 10 days x 24 hours/day x 60 minutes/hour x 60 seconds/minute x 10,000,000 ticks/second
    = -8,640,000,000,000 ticks
    :param i8: integer8 value
    :return: timedelta object
    """

    return datetime.timedelta(seconds=(-1 * i8) / 1e+7)


def bytes_image_to_base64(value):
    """
    Takes a bytes list and returns a base64 str that will be shown right on <img src="">.
    :param value:
    :return:
    """
    try:
        header = binascii.hexlify(value[:4])
        if header.startswith(b"ffd8ff"):
            header = "jpeg"
        elif header == b"89504e47":
            header = "png"
        elif header == b"47494638":
            header = "gif"
        elif header == b'49492a00':
            # This is a tiff image, browser do not support displaying it.
            return None
        else:
            raise ValueError(f"Invalid image. header is {header}, cannot determine if jpeg/png/gif."
                             f"This could be a legitimate error, some iamges aren't parsable")
        return "data:image/{0};base64,{1}".format(header, base64.b64encode(value).decode("utf-8"))
    except Exception:
        raise ValueError(f'Invalid Image. Exception is {get_exception_string()}')


def format_ip_raw(value):
    try:
        address = ipaddress.ip_address(value)
        if isinstance(address, ipaddress.IPv4Address):
            return address._ip
        return None
        # TODO: Add support to ipv6
        # decimal128_ctx = create_decimal128_context()
        # with decimal.localcontext(decimal128_ctx) as ctx:
        # return Decimal128(ctx.create_decimal(str(address._ip)))
    except Exception:
        raise ValueError(f'Invalid raw IP address: {value}')


def parse_unix_timestamp(unix_timestamp):
    try:
        return datetime.datetime.utcfromtimestamp(unix_timestamp)
    except Exception:
        # This must be unix timestamp with milliseconds, we continue to the next line.
        pass
    try:
        return datetime.datetime.utcfromtimestamp(unix_timestamp / 1000)
    except Exception:
        logger.exception(f'problem parsing unix timestamp {unix_timestamp}')
        return None


def is_hostname_valid(hostname):
    return hostname and hostname not in ['host.docker.internal', 'windows10.microdone.cn',
                                         'Screencast-Production-Encoder-to-Prepare-AMI']


def parse_date_with_timezone(datetime_to_parse, time_zone):
    """
    Parses date and returns it as UTC
    """
    try:
        if type(datetime_to_parse) == datetime.datetime:
            # sometimes that happens too
            timezone = pytz.timezone(time_zone)
            return timezone.localize(datetime_to_parse)
        datetime_to_parse = str(datetime_to_parse)
        d = datetime.datetime.strptime(datetime_to_parse, '%Y-%m-%d %H:%M:%S')
        timezone = pytz.timezone(time_zone)
        d = timezone.localize(d)

        # Sometimes, this would be a fake date (see is_date_real). in this case return None
        return d if is_date_real(d) else None
    except (TypeError, ValueError):
        return None


def normalize_timezone_date(date_str: str) -> str:
    """
    Converts given string to a datetime object, along with 'Israel' timezone.
    Parses this date and converts back to str, now in UTC time.

    :param date_str: String representing a date in format %Y-%m-%d %H:%M:%S
    :return:
    """
    parsed_date = parse_date_with_timezone(date_str, 'Israel')
    if not parsed_date:
        return date_str
    return parse_date(parsed_date).strftime('%Y-%m-%d %H:%M:%S')


def is_items_in_list1_are_in_list2(list1, list2):
    if not list1 or not list2:
        return False
    return all(item in list2 for item in list1)


def does_list_startswith(list1, list2):
    """
     by slicing list1 the size of list2 and comparing to list2 we can check if list1 starts with list2
    :param list1: the list to test
    :param list2: the list we want list1 to begin with
    :return: returns True if list1 starts with list2
    """
    return list1[:len(list2)] == list2


def remove_trailing(string, trailing):
    the_len = len(trailing)
    if string[-the_len:] == trailing:
        return string[:-the_len]
    return string


def get_entity_id_for_plugin_name(associated_adapters, plugin_name_key):
    """
    iterates over associated_adapters and returns the entity id of the entity info returned from
        plugin_name_key or None if plugin_name_key is not one of the adapters which returned info on the entity
    :param associated_adapters: the adapters containing all the info of the entity
    :param plugin_name_key: the plugin_unique_name for which to seek the entity id
    """
    return next((entity_id for plugin_unique_name, entity_id in associated_adapters
                 if plugin_name_key == plugin_unique_name), None)


def extract_all_ips(network_ifs):
    """
    :param network_ifs: the network_ifs as appear in the axonius device scheme
    :return: yields every ip in the network interfaces
    """
    from axonius.devices.device_adapter import IPS_FIELD
    if network_ifs is None:
        return
    for network_if in network_ifs:
        for ip in network_if.get(IPS_FIELD) or []:
            yield ip


def normalize_mac(mac):
    if mac:
        return mac.upper().replace('-', '').replace(':', '')


def extract_all_macs(network_ifs):
    """
    :param network_ifs: the network_ifs as appear in the axonius device scheme
    :return: yields every mac in the network interfaces
    """
    from axonius.devices.device_adapter import MAC_FIELD
    if network_ifs is None:
        return
    for network_if in network_ifs:
        current_mac = network_if.get(MAC_FIELD, '')
        if current_mac != '' and current_mac is not None:
            yield normalize_mac(current_mac)


def is_one_subset_of_the_other(first_set, second_set):
    """
    :param first_set: a set
    :param second_set: a set
    :return: True if one of the sets is a subset of the other
    """
    if not first_set or not second_set:
        return False
    return first_set.issubset(second_set) or second_set.issubset(first_set)


def compare_os_type(adapter_device1, adapter_device2):
    from axonius.devices.device_adapter import OS_FIELD
    return adapter_device1['data'][OS_FIELD]['type'] == adapter_device2['data'][OS_FIELD]['type']


def compare_hostname(adapter_device1, adapter_device2):
    return adapter_device1['data']['hostname'].lower() == adapter_device2['data']['hostname'].lower()


def compare_asset_name(adapter_device1, adapter_device2):
    return adapter_device1['data']['name'].lower() == adapter_device2['data']['name'].lower()


def is_different_plugin(adapter_device1, adapter_device2):
    return adapter_device1.get('plugin_name') != adapter_device2.get('plugin_name')


def is_old_device(adapter_device, number_of_days=DEFAULT_NUMBER_OF_DAYS_FOR_OLD_DEVICE):
    """
    This function checks is a default was last seen in the last number_of_days
    """

    try:
        return adapter_device['data'].get('last_seen', datetime.datetime.now()).replace(tzinfo=None) + \
            datetime.timedelta(days=number_of_days) < \
            datetime.datetime.now().replace(tzinfo=None)
    except Exception:
        # If we got exception the default would be assuming it is an old device
        return True


def is_snow_adapter(adapter_device):
    return adapter_device.get('plugin_name') == 'service_now_adapter'


def is_only_host_adapter_not_localhost(adapter_device):
    return (adapter_device.get('plugin_name') in ['deep_security_adapter',
                                                  'cisco_umbrella_adapter',
                                                  'carbonblack_defense_adapter',
                                                  'carbonblack_protection_adapter',
                                                  'csv_adapter',
                                                  'code42_adapter',
                                                  'sysaid_adapter',
                                                  'logrhythm_adapter']) and \
        (not adapter_device.get('data').get('hostname') or
            'localhost' not in adapter_device.get('data').get('hostname').strip().lower())


def is_sccm_or_ad(adapter_device):
    return adapter_device.get('plugin_name') == 'active_directory_adapter' or \
        adapter_device.get('plugin_name') == 'sccm_adapter'


def is_snow_device(adapter_device):
    return adapter_device.get('plugin_name') == 'service_now_adapter'


def is_from_twistlock_or_aws(adapter_device):
    return adapter_device.get('plugin_name') == 'aws_adapter' or \
        adapter_device.get('plugin_name') == 'twistlock_adapter'


def is_azuread_or_ad_and_have_name(adapter_device):
    # Its from ad or azuread and it also has one of these fields not None.
    return adapter_device.get('plugin_name') in ('active_directory_adapter', 'azure_ad_adapter') and \
        get_ad_name_or_azure_display_name(adapter_device)


def is_from_no_mac_adapters_with_empty_mac(adapter_device):
    return (adapter_device['plugin_name'] in ['epo_adapter', 'observeit_adapter', 'cynet_adapter']) and \
           (not adapter_device.get(NORMALIZED_MACS))


def is_from_ad(adapter_device):
    return adapter_device.get('plugin_name') == 'active_directory_adapter'


def is_from_jamf(adapter_device):
    return adapter_device.get('plugin_name') == 'jamf_adapter'


def is_from_ad_or_jamf(adapter_device):
    return adapter_device.get('plugin_name') in ['active_directory_adapter', 'jamf_adapter']


def is_splunk_vpn(adapter_device):
    return adapter_device.get('plugin_name') == 'splunk_adapter' and \
        (adapter_device.get('data') or {}).get('splunk_source') == 'VPN'


def is_illusive_adapter(adapter_device):
    return adapter_device.get('plugin_name') == 'illusive_adapter'


def is_junos_space_device(adapter_device):
    return adapter_device.get('data', {}).get('device_type') == 'Juniper Space Device'


def is_from_juniper_and_asset_name(adapter_device):
    return adapter_device.get('plugin_name') in ['juniper_adapter', 'junos_adapter'] and adapter_device.get('data',
                                                                                                            {}).get(
        'name')


def compare_id(adapter_device1, adapter_device2):
    return get_id(adapter_device1) == get_id(adapter_device2)


def get_os_type(adapter_device):
    from axonius.devices.device_adapter import OS_FIELD
    return (adapter_device['data'].get(OS_FIELD) or {}).get('type')


def is_linux(adapter_device):
    os_type = get_os_type(adapter_device)
    if not os_type:
        return False
    if os_type.lower() == 'linux':
        return True
    return False


def get_id(adapter_device):
    return adapter_device['data'].get('id')


def get_hostname(adapter_device):
    return adapter_device['data'].get('hostname')


def get_domain(adapter_device):
    domain = adapter_device['data'].get('domain')
    if domain:
        return domain.upper()
    return None


def get_last_used_users(adapter_device):
    last_used_user = adapter_device['data'].get('last_used_users')
    if last_used_user:
        return [user.lower().strip() for user in last_used_user if (user and user.strip())]
    return None


def normalize_username(username):
    if not username:
        return None
    username = username.lower()
    if '@' in username:
        username = username.split('@')[0]
    if '\\' in username:
        username = username.split('\\')[1]
    return username


def compare_last_used_users(adapter_device1, adapter_device2):
    users1 = get_last_used_users(adapter_device1)
    users2 = get_last_used_users(adapter_device2)
    if not users1 or not users2:
        return False
    users1 = [normalize_username(username) for username in users1 if normalize_username(username)]
    users2 = [normalize_username(username) for username in users2 if normalize_username(username)]
    if not users1 or not users2:
        return False
    return is_items_in_list1_are_in_list2(users1, users2) or is_items_in_list1_are_in_list2(users2, users1)


def compare_domain(adapter_device1, adapter_device2):
    domain1 = get_domain(adapter_device1)
    domain2 = get_domain(adapter_device2)
    if domain1 and domain2:
        if domain1 in domain2 or domain2 in domain1:
            return True
    return False


def get_normalized_hostname(adapter_device):
    return adapter_device.get(NORMALIZED_HOSTNAME)


def get_normalized_hostname_str(adapter_device):
    return adapter_device.get(NORMALIZED_HOSTNAME_STRING)


def get_ad_name_or_azure_display_name(adapter_device):
    name = adapter_device['data'].get('ad_name') or adapter_device['data'].get('azure_display_name')
    if isinstance(name, str):
        return name.lower()


def compare_ad_name_or_azure_display_name(adapter_device1, adapter_device2):
    name1 = get_ad_name_or_azure_display_name(adapter_device1)
    name2 = get_ad_name_or_azure_display_name(adapter_device2)
    if name1 and name2:
        return name1 == name2
    return False


def get_bios_serial_or_serial(adapter_device):
    serial = adapter_device['data'].get('bios_serial') or adapter_device['data'].get('device_serial')
    if serial is not None:
        serial = str(serial).strip().lower()
        if serial == '' or ('invalid' in serial) or ('none' in serial):
            serial = None
    return serial


def compare_bios_serial_serial(adapter_device1, adapter_device2):
    serial1 = get_bios_serial_or_serial(adapter_device1)
    serial2 = get_bios_serial_or_serial(adapter_device2)
    if serial1 is not None and serial2 is not None:
        return serial1 == serial2
    return False


def get_bios_serial_or_serial_no_s(adapter_device):
    serial = get_bios_serial_or_serial(adapter_device)
    if serial:
        serial = serial.strip('s')
    return serial


def get_hostname_or_serial(adapter_device):
    serial = get_serial(adapter_device)
    if serial:
        return serial.lower()
    hostname = get_hostname(adapter_device)
    if hostname:
        return hostname.split('.')[0].lower()
    return None


def compare_hostname_serial(adapter_device1, adapter_device2):
    host_serial_1 = get_hostname_or_serial(adapter_device1)
    host_serial_2 = get_hostname_or_serial(adapter_device2)
    if host_serial_1 and host_serial_2 and host_serial_1 == host_serial_2:
        return True
    return False


def compare_bios_serial_serial_no_s(adapter_device1, adapter_device2):
    serial1 = get_bios_serial_or_serial_no_s(adapter_device1)
    serial2 = get_bios_serial_or_serial_no_s(adapter_device2)
    if serial1 is not None and serial2 is not None:
        return serial1 == serial2
    return False


def get_asset_name(adapter_device):
    return adapter_device['data'].get('name')


def get_serial(adapter_device):
    serial = (adapter_device['data'].get('device_serial') or '').strip()
    if serial and serial.upper().strip() != 'INVALID' and 'VMWARE' not in serial.upper().strip():
        return serial.upper()
    return None


def get_serial_no_s(adapter_device):
    serial = get_serial(adapter_device)
    if not serial:
        return None
    return serial.strip('S')


def compare_serial_no_s(adapter_device1, adapter_device2):
    serial1 = get_serial_no_s(adapter_device1)
    serial2 = get_serial_no_s(adapter_device2)
    return serial1 and serial2 and serial1 == serial2


def get_asset_snow_or_host(adapter_device):
    if adapter_device.get('plugin_name') == 'service_now_adapter':
        asset = get_asset_name(adapter_device)
    else:
        asset = get_hostname(adapter_device)
    if asset:
        return asset.lower().strip()
    return None


def compare_snow_asset_hosts(adapter_device1, adapter_device2):
    asset1 = get_asset_snow_or_host(adapter_device1)
    asset2 = get_asset_snow_or_host(adapter_device2)
    if asset1 and asset2 and asset1 == asset2:
        return True
    return False


def get_asset_or_host(adapter_device):
    asset = get_asset_name(adapter_device) or get_hostname(adapter_device)
    if asset:
        return asset.split('.')[0].lower().strip()
    return None


def compare_asset_hosts(adapter_device1, adapter_device2):
    asset1 = get_asset_or_host(adapter_device1)
    asset2 = get_asset_or_host(adapter_device2)
    if asset1 and asset2 and asset1 == asset2:
        return True
    return False


def get_cloud_data(adapter_device):
    adapter_device_data = adapter_device.get('data') or {}

    cloud_provider = adapter_device_data.get('cloud_provider')
    cloud_id = adapter_device_data.get('cloud_id')

    if isinstance(cloud_provider, str) and isinstance(cloud_id, str) and len(cloud_provider) > 0 and len(cloud_id) > 0:
        return cloud_provider.upper().strip() + "-" + cloud_id.upper().strip()

    return None


def compare_clouds(adapter_device1, adapter_device2):
    cloud1 = get_cloud_data(adapter_device1)
    cloud2 = get_cloud_data(adapter_device2)

    if cloud1 is not None and cloud2 is not None:
        return cloud1 == cloud2

    return False


def has_mac_or_ip(adapter_data):
    """
    checks if one of the network interfaces in adapter data has a MAC or ip
    :param adapter_data: the data of the adapter to test
    :return: True if there's at least one MAC or IP
    """
    from axonius.devices.device_adapter import NETWORK_INTERFACES_FIELD, IPS_FIELD, MAC_FIELD
    return any(x.get(IPS_FIELD) or x.get(MAC_FIELD) for x in (adapter_data.get(NETWORK_INTERFACES_FIELD) or []))


def normalize_hostname(adapter_data):
    hostname = adapter_data.get('hostname')
    if hostname is not None:
        final_hostname = hostname.upper()
        adapter_data['hostname'] = final_hostname
        final_hostname = final_hostname.replace(' ', '-')
        final_hostname = final_hostname.replace('\'', '')
        final_hostname = final_hostname.replace('’', '')
        for extension in DEFAULT_DOMAIN_EXTENSIONS:
            final_hostname = remove_trailing(final_hostname, extension)
        split_hostname = final_hostname.split('.')

        return split_hostname


def compare_normalized_hostnames(host1, host2, first_element_only=False) -> bool:
    """
    As mentioned above in the documentation near the definition of NORMALIZED_HOSTNAME we want to compare hostnames not
    based on the domain as some adapters don't return one or return a default one even when one exists. After we
    split each host name on "." if one list starts with the other - one hostname is the beginning of the other not
    including the domain - which means in our view - they are the same - for example:
    1. ubuntuLolol.local == ubuntulolol.workgroup  --- because both have a default domain
    2. ubuntuLolol.local == ubuntulolol.axonius  --- because one has a default domain and the other has a normal one
        when normalizing this would become ['ubuntuLolol'], ['ubuntulolol','axonius'] and list2 starts with list1
    3. ubuntuLolol.local.axonius != ubuntulolol.9 as when normalizing they'd become
        ['ubuntuLolol', 'local', 'axonius'], ['ubuntulolol', '9'] and no list is the beginning of the other.
    """
    if first_element_only:
        if len(host1) > 0 and len(host2) > 0 and host1[0] != '' and host2[0] != '':
            return host1[0][:15] == host2[0][:15]
        else:
            return False
    else:
        return host1 and host2 and (does_list_startswith(host1, host2) or
                                    does_list_startswith(host2, host1))


def have_mac_intersection(adapter_device1, adapter_device2) -> bool:
    """
    In these case we are looking for mac intersections. We do that in cases where hostname are equals,
    but IPs contradict. This can happens for various reasons at agents. If we have some mac which is equals,
    this is enough for correlation
    :param adapter_device1:
    :param adapter_device2:
    :return Whether there is at least one mac in both adapter_devices:
    """
    device1_macs = set(adapter_device1.get(NORMALIZED_MACS) or [])
    device2_macs = set(adapter_device2.get(NORMALIZED_MACS) or [])
    return bool(device1_macs.intersection(device2_macs))


def ips_do_not_contradict_or_mac_intersection(adapter_device1, adapter_device2):
    return ips_do_not_contradict(adapter_device1, adapter_device2) or have_mac_intersection(adapter_device1,
                                                                                            adapter_device2)


def ips_do_not_contradict(adapter_device1, adapter_device2):
    device1_ips = adapter_device1.get(NORMALIZED_IPS)
    device2_ips = adapter_device2.get(NORMALIZED_IPS)
    return not device1_ips or not device2_ips or is_one_subset_of_the_other(device1_ips, device2_ips)


def macs_do_not_contradict(adapter_device1, adapter_device2):
    device1_macs = adapter_device1.get(NORMALIZED_MACS)
    device2_macs = adapter_device2.get(NORMALIZED_MACS)
    return not device1_macs or not device2_macs or is_one_subset_of_the_other(device1_macs, device2_macs)


def snow_asset_names_do_not_contradict(adapter_device1, adapter_device2):
    if not is_snow_adapter(adapter_device1) or not is_snow_adapter(adapter_device2):
        return True
    asset1 = get_asset_name(adapter_device1)
    asset2 = get_asset_name(adapter_device2)
    if asset1 and asset2 and asset1.lower() != asset2.lower():
        return False
    return True


def asset_hostnames_do_not_contradict(adapter_device1, adapter_device2):
    return hostnames_do_not_contradict(adapter_device1, adapter_device2) and \
        snow_asset_names_do_not_contradict(adapter_device1, adapter_device2)


def serials_do_not_contradict(adapter_device1, adapter_device2):
    serial1 = get_serial(adapter_device1)
    serial2 = get_serial(adapter_device2)
    if not serial1 or not serial2:
        return True
    return serial1 == serial2


def hostnames_do_not_contradict(adapter_device1, adapter_device2):
    if not get_hostname(adapter_device1) or not get_hostname(adapter_device2):
        return True
    return compare_device_normalized_hostname(adapter_device1, adapter_device2)


def not_contain_generic_jamf_names(adapter_device1, adapter_device2):
    return not contain_jamf_generic_names(adapter_device1) or not contain_jamf_generic_names(adapter_device2)


def contain_jamf_generic_names(adapter_device):
    hostname = get_hostname(adapter_device)
    if not hostname:
        return False
    if 'MacBook Pro (' in hostname:
        return True
    return False


def cloud_id_do_not_contradict(adapter_device1, adapter_device2):
    cloud_id_1 = get_cloud_data(adapter_device1)
    cloud_id_2 = get_cloud_data(adapter_device2)
    if not cloud_id_1 or not cloud_id_2:
        return True
    return cloud_id_1 == cloud_id_2


def compare_ips(adapter_device1, adapter_device2):
    return is_one_subset_of_the_other(adapter_device1.get(NORMALIZED_IPS), adapter_device2.get(NORMALIZED_IPS))


def os_not_contradict(adapter_device1, adapter_device2):
    os_type1 = get_os_type(adapter_device1)
    os_type2 = get_os_type(adapter_device2)
    if os_type1 and os_type2 and 'Windows' in [os_type1, os_type2] and 'OS X' in [os_type1, os_type2]:
        return False
    return True


def compare_macs_or_one_is_jamf(adapter_device1, adapter_device2):
    return (compare_macs(adapter_device1, adapter_device2) or is_from_jamf(adapter_device1) or
            is_from_jamf(adapter_device2)) and os_not_contradict(adapter_device1, adapter_device2)


def compare_macs(adapter_device1, adapter_device2):
    return is_one_subset_of_the_other(adapter_device1.get(NORMALIZED_MACS), adapter_device2.get(NORMALIZED_MACS))


def compare_device_normalized_hostname(adapter_device1, adapter_device2) -> bool:
    """
    See compare_normalized_hostnames docs
    :param adapter_device1: first device
    :param adapter_device2: second device
    :return:
    """
    def is_in_short_names_adapters_and_long_name(adapter_device):
        if adapter_device.get('plugin_name') in ['carbonblack_protection_adapter', 'active_directory_adapter',
                                                 'lansweeper_adapter', 'sccm_adapter'] \
                and len(get_hostname(adapter_device).split('.')[0]) == NET_BIOS_MAX_LENGTH:
            return True
        return False

    first_element_only = False
    if is_in_short_names_adapters_and_long_name(adapter_device2):
        first_element_only = True
    if is_in_short_names_adapters_and_long_name(adapter_device1):
        first_element_only = True
    return compare_normalized_hostnames(adapter_device1.get(NORMALIZED_HOSTNAME),
                                        adapter_device2.get(NORMALIZED_HOSTNAME),
                                        first_element_only)


def get_normalized_ip(adapter_device):
    return adapter_device.get(NORMALIZED_IPS)


def normalize_adapter_devices(devices):
    """
    in order to save a lot of time later - we normalize the adapter devices.
        every adapter_device with an ip or mac is given a corresponding set in the root of the adapter_device.
        we upper the hostname of every adapter_device with a hostname
        we upper the os type of every adapter_device with a os type
    :param devices: all of the devices to be correlated
    :return: a normalized list of the adapter_devices
    """
    for device in devices:
        for adapter_device in device['adapters']:
            yield normalize_adapter_device(adapter_device)
        for tag in device.get('tags', []):
            if tag.get('entity') == EntityType.Devices.value and \
                    tag.get('type') == 'adapterdata' and \
                    tag.get('associated_adapter_plugin_name') and \
                    len(tag.get('associated_adapters', [])) == 1:
                yield normalize_adapter_device(tag)


def normalize_adapter_device(adapter_device):
    """
    See normalize_adapter_devices
    """
    from axonius.devices.device_adapter import OS_FIELD, NETWORK_INTERFACES_FIELD
    adapter_data = adapter_device['data']
    if has_mac_or_ip(adapter_data):
        ips = set(extract_all_ips(adapter_data[NETWORK_INTERFACES_FIELD]))
        macs = set(extract_all_macs(adapter_data[NETWORK_INTERFACES_FIELD]))
        adapter_device[NORMALIZED_IPS] = ips if len(ips) > 0 else None
        adapter_device[NORMALIZED_MACS] = macs if len(macs) > 0 else None
    # Save the normalized hostname so we can later easily compare.
    # See further doc near definition of NORMALIZED_HOSTNAME.
    adapter_device[NORMALIZED_HOSTNAME] = normalize_hostname(adapter_data)
    if adapter_device[NORMALIZED_HOSTNAME]:
        adapter_device[NORMALIZED_HOSTNAME_STRING] = '.'.join(adapter_device[NORMALIZED_HOSTNAME]) + '.'
    if adapter_data.get(OS_FIELD) is not None and adapter_data.get(OS_FIELD, {}).get('type'):
        adapter_data[OS_FIELD]['type'] = adapter_data[OS_FIELD]['type'].upper()
    return adapter_device


def inverse_function(x: FunctionType) -> FunctionType:
    """
    Returns the inverse of a boolean function
    """

    def tmp(*args, **kwargs):
        return not x(*args, **kwargs)

    return tmp


def or_function(*functions) -> FunctionType:
    """
    Returns a function that represents the OR of the provided functions
    """

    def tmp(*args, **kwargs):
        for func in functions:
            if func(*args, **kwargs):
                return True
        return False

    return tmp


def and_function(*functions) -> FunctionType:
    """
    Returns a function that represents the AND of the provided functions
    """

    def tmp(*args, **kwargs):
        for func in functions:
            if not func(*args, **kwargs):
                return False
        return True

    return tmp


def make_dict_from_csv(csv_data):
    return csv.DictReader(csv_data.splitlines(), dialect=csv.Sniffer().sniff(csv_data.splitlines()[0],
                                                                             delimiters=[',', '\t']))


def remove_duplicates_by_reference(seq):
    """
     order preserving duplicate reference removing
     benchmark: 1.91 ms ± 28.8 µs for 20k values on i7 7700HQ
     """
    seen = {}
    result = []
    for item in seq:
        marker = id(item)
        if marker in seen:
            continue
        seen[marker] = 1
        result.append(item)
    return result


def remove_large_ints(data, name: str):
    """
    Go over a dict and remove any number which is larger than 8 bytes, since MongoDB can't eat it.
    :param data: the
    """
    if isinstance(data, int) and data > (2 ** 64) - 1:
        logger.warning(f'Warning! removing {name} with value {data} '
                       f'since its larger than 8 bytes!')
        return TO_REMOVE_VALUE

    if isinstance(data, dict):
        new_dict = dict()
        for key, value in data.items():
            new_value = remove_large_ints(value, f'{name}_{key}')
            if new_value is not TO_REMOVE_VALUE:
                new_dict[key] = new_value

        return new_dict

    if isinstance(data, list):
        new_list = []
        for i, value in enumerate(data):
            new_value = remove_large_ints(value, f'{name}_{i}')
            if new_value is not TO_REMOVE_VALUE:
                new_list.append(new_value)

        return new_list

    return data
