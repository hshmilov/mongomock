"""
ParsingUtils.py: Collection of utils that might be used by parsers, specifically adapters
"""
import base64
import binascii
import csv
import datetime
import html
import ipaddress
import logging
import os
import re
import string
import sys
import uuid
from types import FunctionType
from typing import Callable, NewType, List, Iterable, Optional

import pytz

import axonius
from axonius.consts.system_consts import GENERIC_ERROR_MESSAGE
from axonius.entities import EntityType
from axonius.utils.datetime import is_date_real, parse_date, _parse_unix_timestamp
from axonius.devices.msft_versions import parse_msft_release_version

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
OSX_NAMES = ['mojave', 'sierra', 'capitan', 'yosemite', 'mavericks', 'darwin', 'catalina']
MAC_NAMES = ['os x', 'osx', 'macos', 'mac os', 'macbook']
# In some cases we don't want to use compare_hostnames because indexing using it is complicated
# and in some cases indexsing is performance critical
NORMALIZED_HOSTNAME_STRING = 'normalized_hostname_string'
NET_BIOS_MAX_LENGTH = 15
DEFAULT_DOMAIN_EXTENSIONS = ['.LOCAL', '.WORKGROUP', '.LOCALHOST']
# In MacOs hostname of the same computer can return in different shapes,
# that's why we would like to compare them without these strings
DEFAULT_MAC_EXTENSIONS = ['-MACBOOK-PRO', 'MACBOOK-PRO', '-MBP', 'MBP', '-MBA', '-MACBOOK-AIR', 'MACBOOK-AIR'] + \
                         [f'-MBP-{index}' for index in range(20)] + \
                         [f'-MBP-0{index}' for index in range(10)] + ['-AIR', 'AIR'] + \
                         [f'-MACBOOK-PRO-{index}' for index in range(20)] + \
                         [f'-MACBOOK-PRO-0{index}' for index in range(10)] + \
                         [f'MACBOOKPRO{index}' for index in range(20)] + [f'MACBOOKPRO0{index}' for index in range(10)]
# NORMALIZED_IPS/MACS fields will hold the set of IPs and MACs an adapter devices has extracted.
# Without it, in order to compare IPs and MACs we would have to go through the list of network interfaces and extract
# them each time.
NORMALIZED_IPS = 'normalized_ips'
NORMALIZED_IPS_4 = 'normalized_ips_4'
NORMALIZED_IPS_6 = 'normalized_ips_6'
NORMALIZED_MACS = 'normalized_macs'
ALLOWED_VAR_CHARACTERS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'

# Constants for parsing and formatting software versions in order to compare
# them in the query wizard
N_CHAR_EXTENSION = 8
DEFAULT_VERSION_EXTENSION = '00000000'
DEFAULT_LINUX_VERSION_EPOCH = '0'
BAD_SERIALS = ['INVALID', 'NON-UNIQUES/N', '0', 'SYSTEMSERIALNUMBER', 'TOBEFILLEDBYO.E.M.', 'VIRTUAL',
               'DEFAULTSTRING', 'NA', 'N/A', '123456789', 'UNKNOWN', '-', '0123456789', 'NA-VIRTUAL',
               '0123456789ABCDEF']


# This number stands for the default number of days needed for us to say a device is old,
# first use if for correlation at is_old_device
DEFAULT_NUMBER_OF_DAYS_FOR_OLD_DEVICE = 7

TO_REMOVE_VALUE = object()

BSON_SPEC_MAX_INT = 0x7fffffffffffffff
pair_comparator = NewType('pair_comparator', FunctionType)
parameter_function = NewType('parameter_function', Callable)

# New versions can be downloaded from the following resources:
# https://github.com/wireshark/wireshark/raw/master/manuf
# https://gitlab.com/wireshark/wireshark/raw/master/manuf
# https://code.wireshark.org/review/gitweb?p=wireshark.git;a=blob_plain;f=manuf;hb=HEAD
oui_data = open(os.path.join(axonius.__path__[0], 'manuf'), encoding='utf8').read()

# dict: MAC 3 first bytes to manufacturer data
mac_manufacturer_details = {x[0].replace(':', ''): x for x in [x.split('\t') for x
                                                               in oui_data[oui_data.find('00:00:00'):].splitlines()]}
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
    elif type(bool_raw_value) == str and bool_raw_value.lower() in ['true', 'false', '0', '1']:
        return bool_raw_value.lower() in ['true', '1']

    if raise_on_exception is True:
        raise ValueError(f'{bool_raw_value} isn\'t a boolean value')

    else:
        return None


def int_or_none(val):
    if val is None:
        return None
    try:
        return int(val)
    except Exception:
        return None


def float_or_none(val):
    if val is None:
        return None
    try:
        return float(val)
    except Exception:
        return None


def get_manufacturer_from_mac(mac: str) -> Optional[str]:
    if mac:
        try:
            formatted_mac = format_mac(mac).replace(':', '')
            for index in [6, 7, 8, 9]:
                manufacturer = mac_manufacturer_details.get(formatted_mac[:index])
                if manufacturer:
                    if len(manufacturer) > 2:
                        return f'{manufacturer[1]} ({manufacturer[2]})'
                    else:
                        return f'{manufacturer[1]}'
            return None
        except Exception as e:
            logger.exception(f'Error in parsing mac vendor: {e}')
            return None
    return None


def normalize_var_name(name):
    """
    Takes a string and returns another string which can be a variable name in python.
    :param name:
    :return:
    """
    name = name.replace('-', '_').replace(' ', '_')
    name = ''.join([character for character in name if character in ALLOWED_VAR_CHARACTERS])
    return name


def get_exception_string(force_show_traceback=False):
    """
    when inside a catch exception flow, returns a really informative string representing it.
    :param: force_show_traceback, force returning the trackback to user even if in production mode
    :return: a string representing the exception.
    """
    exc_type, exc_obj, exc_tb = sys.exc_info()

    ex_str = 'Traceback (most recent call last):\n'
    while exc_tb is not None:
        ex_str = ex_str + '  File {0}, line {1}, in {2}\n'.format(
            exc_tb.tb_frame.f_code.co_filename,
            exc_tb.tb_lineno,
            exc_tb.tb_frame.f_code.co_name)

        exc_tb = exc_tb.tb_next

    ex_str = ex_str + f'{exc_type}:{exc_obj}'
    exc_id = uuid.uuid4()
    logger.error(f'UUID {exc_id}: error traceback: {ex_str}')
    return html.escape(ex_str) if os.environ.get('PROD') == 'false' or force_show_traceback \
        else GENERIC_ERROR_MESSAGE.format(exc_id)


def figure_out_cloud(s):
    """
    Figures out a cloud provider. If we can't find it, returns None.
    :param s: the cloud provider, e.g. "amazon-web-services"
    :return: a generic value representing the cloud provider, which you can use for device.cloud_provider
    """
    if not s:
        return None

    cloud_provider = s.lower()

    if 'aws' in cloud_provider or 'amazon' in cloud_provider:
        return 'AWS'
    elif 'azure' in cloud_provider or 'microsoft' in cloud_provider:
        return 'Azure'
    elif 'google' in cloud_provider or 'gcp' in cloud_provider:
        return 'GCP'
    elif 'softlayer' in cloud_provider or 'ibm' in cloud_provider:
        return 'Softlayer'
    elif 'vmware' in cloud_provider or 'vcenter' in cloud_provider \
            or 'vsphere' in cloud_provider or 'esx' in cloud_provider:
        return 'VMWare'
    elif 'alibaba' in cloud_provider or 'aliyun' in cloud_provider:
        return 'Alibaba'
    elif 'oracle' in cloud_provider:
        return 'Oracle'
    else:
        return None


def figure_out_windows_dist(s):
    win_ver = parse_msft_release_version(s.lower())
    if win_ver is not None:
        return win_ver

    # We do this to avoid cases like "Windows 10 XXX 2016"
    if 'windows 10 ' in s.lower() and 'server' not in s.lower():
        return '10'
    s = s.replace('Windows ', '').replace('Windows', '').replace('Win', '')
    dist_name = ''
    if 'server' in s or 'windows 2003' in s or 'windows 2008' in s or 'windows 2012' in s or 'windows 2016' in s:
        dist_name = f'{dist_name} Server'
    else:
        dists_with_no_version = ['Vista', 'XP']
        for dist in dists_with_no_version:
            if dist.lower() in s:
                return dist
    dist_versions = ['2000', '2003', '2008', '2012', '2016', '2019']
    dist_versions.extend([' 10', ' 8.1', ' 95', ' 98', ' 8', ' 7'])
    for version in dist_versions:
        if version in s:
            dist_name = f'{dist_name} {version.strip()}'
            break
    if not dist_name.strip():
        return None
    return dist_name.strip()


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

    is_windows_server = False
    bitness = None
    if any(x in s for x in makes_64bit):
        bitness = 64
    elif any(x in s for x in makes_32bit):
        bitness = 32

    os_type = None
    distribution = None
    linux_names = ['linux', 'ubuntu', 'canonical', 'red hat',
                   'debian', 'fedora', 'centos', 'oracle', 'opensuse', 'rhel server', 'sles', 'gentoo', 'arch']

    ios_devices = ['iphone', 'ipad', 'apple']
    ios_names = ios_devices + ['ios']

    # Start with the one who have for sure capital in their names
    # The first part is not enough, since some devices have only 'IOS' in them, but not "cisco".
    # We have seen this happening in clients (a device with 2 adapters had "Cisco", "iOS" operating systems,
    # in a client that did not let us connect to any system that see mobile devices)
    if 'cisco' in s or ('IOS' in orig_s and not any(x in s for x in ios_devices)):
        # If it has 'cisco', or it has 'IOS' (upper letters) and it doesn't have 'iphone', 'ipad', etc.
        os_type = 'Cisco'
    elif 'vxworks' in s:
        os_type = 'VxWorks'
    elif 'windows' in s or ('win' in s and 'darwin' not in s):
        os_type = 'Windows'
        distribution = figure_out_windows_dist(s)
        if distribution and 'server' in distribution.lower():
            is_windows_server = True
    elif 'android' in s:
        os_type = 'Android'
        version = mobile_version.findall(s)
        if len(version):
            distribution = version[0]
    elif any(x in s for x in linux_names):
        os_type = 'Linux'
        linux_distributions = [ubuntu_full, 'Ubuntu', 'Red Hat', 'Debian', 'Fedora', 'RHEL', 'Gentoo',
                               'Arch', 'Oracle', 'SuSe', 'Centos']
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

    elif any(elem in s for elem in MAC_NAMES) \
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
        os_type = 'FreeBSD'
        distribution = 'FreeBSD'
    elif 'junos' in s:
        os_type = 'FreeBSD'
        distribution = 'Junos OS'
    elif s.startswith('vmware'):
        os_type = 'VMWare'
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
        distribution = s.replace('VMWare ', '')
        if distribution not in esx_distributions:
            distribution = '(?) ' + distribution
    elif 'mikrotik' in s.lower():
        os_type = 'Mikrotik'
    elif 'f5 networks big-ip' == s.lower():
        os_type = 'F5 Networks Big-IP'
    elif 'solaris' in s.lower():
        os_type = 'Solaris'
    elif 'aix' in s.lower():
        os_type = 'AIX'
    elif 'printer' in s.lower():
        os_type = 'Printer'
    elif 'playstation' in s.lower():
        os_type = 'PlayStation'
    elif 'check point' in s.lower():
        os_type = 'Check Point'
    elif 'netscaler' in s.lower():
        os_type = 'Netscaler'

    return_dict = {'type': os_type,
                   'distribution': distribution,
                   'bitness': bitness,
                   'os_str': s}
    if os_type == 'Windows':
        return_dict['is_windows_server'] = is_windows_server
    return return_dict


def convert_ldap_searchpath_to_domain_name(ldap_search_path):
    """
    Converts LDAP search path to DC.
    e.g. 'CN=DESKTOP-MPP10U1,CN=Computers,DC=TestDomain,DC=test' -> 'TestDomain.test'
    :param ldap_search_path: the str
    :return:
    """

    return '.'.join([x[3:] for x in ldap_search_path.strip().split(',') if x.lower().startswith('dc=')])


def get_organizational_units_from_dn(distinguished_name):
    try:
        ous = [ou[3:] for ou in distinguished_name.split(',') if ou.startswith('OU=')]
        if ous:
            return ous
        return None
    except Exception:
        return None


def is_domain_valid(domain):
    """
    :param doomain: e.g. TestDomain
    :return: e.g. Whether domain exist and has a valid value which is not a local value
    """
    domain = (domain or '').strip().lower()
    if domain and not 'workgroup' in domain and not 'local' == domain and \
            not 'n/a' in domain and not '(none)' in domain:
        return True
    return False


def not_wifi_adapters(adapter_device1, adapter_device2):
    return not_wifi_adapter(adapter_device1) and not_wifi_adapter(adapter_device2)


def not_wifi_adapter(adapter_device):
    if adapter_device.get('plugin_name').lower() == 'aruba_adapter' or \
            (adapter_device.get('plugin_name').lower() == 'cisco_prime_adapter' and
             adapter_device['data'].get('fetch_proto') == 'PRIME_WIFI_CLIENT') or\
            (adapter_device.get('plugin_name').lower() == 'tanium_discover_adapter'):
        if adapter_device.get(NORMALIZED_MACS):
            return False
    return True


def get_first_object_from_dn(dn):
    """
    :param dn: e.g. CN=Administrator,CN=Users,DC=TestDomain,DC=test
    :return: e.g. Administrator
    """
    if type(dn) == str:
        dn = dn.replace('\\,', '')
        dn = dn.split(',')
        if len(dn) > 0:
            # This usually looks like CN=User Name, CN=Users, DC=.... so lets take the first one
            rv = dn[0].split('=')
            if len(rv) == 2:
                return rv[1]

    return None


def get_member_of_list_from_memberof(member_of) -> List[str]:
    try:
        if member_of is not None:
            # member_of is a list of dn's that look like 'CN=d,OU=b,DC=c,DC=a'
            # so we take each string in the list and transform it to d.b.c.a
            return ['.'.join([x[3:] for x in member_of_entry.strip().split(',')]) for member_of_entry in member_of]
    except Exception:
        pass

    return None


def is_valid_user(username: str) -> bool:
    if not isinstance(username, str):
        return False
    return username.strip().lower() not in ['n/a', '<none>', 'none', 'unknown']


def is_valid_ip(ip):
    try:
        ipaddress.ip_address(ip)
        return True
    except Exception:
        return False


def is_valid_ipv4(ip):
    """Check if an ip address is in valid IPv4 format.

    :param ip: IP address to check.
    :type ip: str
    :rtype: bool
    """
    try:
        return isinstance(ipaddress.ip_address(ip), ipaddress.IPv4Address)
    except Exception:
        return False


def is_valid_ipv6(ip):
    """Check if an ip address is in valid IPv6 format.

    :param ip: IP address to check.
    :type ip: str
    :rtype: bool
    """
    try:
        return isinstance(ipaddress.ip_address(ip), ipaddress.IPv6Address)
    except Exception:
        return False


def guaranteed_list(x):
    if not x:
        return []
    elif isinstance(x, list):
        return x
    else:
        return [x]


def format_mac(mac: str):
    if mac is None or mac == '':
        return None
    mac = re.sub('[.:-]', '', mac).lower()  # remove delimiters and convert to lower case
    mac = ''.join(mac.split())  # remove whitespaces

    if len(mac) != 12 or any(map(lambda char: char not in string.hexdigits, mac)):
        raise ValueError(f'Invalid mac {mac}')

    # convert mac in canonical form (eg. 00:80:41:ae:fd:7e)
    mac = ':'.join(['%s' % (mac[i:i + 2]) for i in range(0, 12, 2)])
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
        if header.startswith(b'ffd8ff'):
            header = 'jpeg'
        elif header == b'89504e47':
            header = 'png'
        elif header == b'47494638':
            header = 'gif'
        elif header == b'49492a00':
            # This is a tiff image, browser do not support displaying it.
            return None
        else:
            raise ValueError(f'Invalid image. header is {header}, cannot determine if jpeg/png/gif.'
                             f'This could be a legitimate error, some iamges aren\'t parsable')
        return 'data:image/{0};base64,{1}'.format(header, base64.b64encode(value).decode('utf-8'))
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


def parse_versions_raw(version):
    """
    Gets a software version number and formats it so it can be compared in
    the query wizard
    :param version:
    :return:
    """
    try:
        if not version or not isinstance(version, str):
            return ''
        version = version.strip()
        # Even if the version is not linux software, the input is formatted as if it were
        # (meaning it has a leading 0) because it may or may not be comparing linux
        # software versions, so all versions need to have the same alignment (meaning they
        # start with a leading 0)
        extended_version = DEFAULT_LINUX_VERSION_EPOCH

        # Check for linux software since it has different, inconsistent format
        if any(word in version for word in ['ubuntu', 'dsfg', 'dsf', 'build', '-', '~', '+', ':']):
            extended_version = parse_linux_software_versions_raw(version)
            return extended_version

        split_on_dot = version.split('.')

        for field in split_on_dot:
            try:
                if not str.isdigit(field):
                    return ''
                # If the existing version is longer than the n characters each field is allotted, trim it
                if len(field) > N_CHAR_EXTENSION:
                    field = field[:N_CHAR_EXTENSION]
                extended_version += extend_to_n_digits(field, N_CHAR_EXTENSION)
            except Exception:
                logger.exception(f'Problem parsing version {version}')
                return ''

        return extended_version

    except Exception:
        logger.exception(f'Could not parse software version {version}')
        return ''


def extend_to_n_digits(value, n_chars_to_extend):
    try:
        extended_value = ''.join(['0' for _ in range(n_chars_to_extend - len(value))])
        extended_value += value
        return extended_value
    except Exception:
        logger.exception(f'Problem extending version field {value}')
        return ''


def parse_linux_software_versions_raw(version):
    """
    Only parses the version for the source (the first version listed), doesn't
    handle the rest of the version
    :param version:
    :return:
    """
    try:
        extended_version = DEFAULT_LINUX_VERSION_EPOCH      # If no explicit epoch, it has an implied 0
        if ':' in version:
            extended_version = version.split(':')[0]
            version = str(version.split(':')[1])
        to_split = version.replace('~', '-').replace('+', '-').replace('ubuntu', '-')
        primary_version = to_split.split('-')[0]
        for field in primary_version.split('.'):
            if not str.isdigit(field):
                return ''
            extended_version += extend_to_n_digits(field, N_CHAR_EXTENSION)
        return extended_version
    except Exception:
        logger.exception(f'Problem parsing linux software version {version}')
        return ''


def parse_unix_timestamp(unix_timestamp):
    return _parse_unix_timestamp(unix_timestamp)


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
            if ip not in ['127.0.0.1']:
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
    hostname1 = adapter_device1['data'].get('hostname')
    hostname2 = adapter_device2['data'].get('hostname')
    if not hostname1 or not hostname2:
        return False
    return hostname1.lower() == hostname2.lower()


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


def is_airwtch_adapter(adapter_device):
    return adapter_device.get('plugin_name') == 'airwatch_adapter'


def is_lansweerp_dapter(adapter_device):
    return adapter_device.get('plugin_name') == 'lansweeper_adapter'


def is_alertlogic_adapter(adapter_device):
    return adapter_device.get('plugin_name') == 'alertlogic_adapter'


def is_bluecat_adapter(adapter_device):
    return adapter_device.get('plugin_name') == 'bluecat_adapter'


def is_qualys_adapter(adapter_device):
    return adapter_device.get('plugin_name') == 'qualys_scans_adapter'


def is_tenable_io_adapter(adapter_device):
    return adapter_device.get('plugin_name') == 'tenable_io_adapter'


def is_g_naapi_adapter(adapter_device):
    return adapter_device.get('plugin_name') == 'g_naapi_adapter'


def is_counter_act_adapter(adapter_device):
    return adapter_device.get('plugin_name') == 'counter_act_adapter'


def is_sql_adapter(adapter_device):
    return adapter_device.get('plugin_name') in ['mssql_adapter', 'mysql_special_adapter']


def is_aqua_adapter(adapter_device):
    return adapter_device.get('plugin_name') == 'aqua_adapter'


def is_dangerous_asset_names_adapter(adapter_device):
    return is_snow_adapter(adapter_device) or is_lansweerp_dapter(adapter_device) \
        or is_alertlogic_adapter(adapter_device) \
        or is_bluecat_adapter(adapter_device) or is_qualys_adapter(adapter_device) \
        or is_counter_act_adapter(adapter_device) or is_sql_adapter(adapter_device) or is_aqua_adapter(adapter_device)


def hostname_not_problematic(adapter_device):
    if (not get_normalized_hostname_str(adapter_device) or
            ('localhost' not in get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower()
             and 'iphone' not in get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower()
             and 'ipad' not in get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower()
             and 'blank' != get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower()
             and 'loaner' != get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower()
             and 'macbook-air' != get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower()
             and 'mac-mini' != get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower()
             and 'billing' != get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower()
             and 'work' != get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower()
             and 'fullservice' != get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower()
             and 'harmony' != get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower()
             and 'cs' != get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower()
             and 'timeclock' != get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower()
             and 'ops' != get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower()
             and 'null' != get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower()
             and 'n/a' != get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower()
             and 'itadmins-macbook-pro' != get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower()
             and 'macbook pro' != get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower()
             and 'macbook-pro_root' != get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower()
             and 'dev' != get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower()
             and 'delete' not in get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower()
             and 'playtikas-macbook-pro' not in get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower()
             and 'unknown' not in get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower()
             and 'macbook-pro' != get_normalized_hostname_str(adapter_device).split('.')[0].strip().lower())):
        return True
    return False


def is_sccm_or_ad(adapter_device):
    return adapter_device.get('plugin_name') == 'active_directory_adapter' or \
        adapter_device.get('plugin_name') == 'sccm_adapter'


def is_snow_device(adapter_device):
    return adapter_device.get('plugin_name') == 'service_now_adapter'


def is_from_deeps_tenable_io_or_aws(adapter_device):
    return (adapter_device.get('plugin_name') == 'aws_adapter' and
            adapter_device['data'].get('aws_device_type') == 'EC2') \
        or adapter_device.get('plugin_name') in ['deep_security_adapter', 'tenable_io_adapter']


def get_cloud_id_or_hostname(adapter_device):
    cloud_id = adapter_device['data'].get('cloud_id')
    if cloud_id:
        return cloud_id.lower()
    if get_hostname(adapter_device):
        return get_hostname(adapter_device).lower()
    return None


def get_dns_names(adapter_device):
    dns_names = adapter_device['data'].get('dns_names')
    if dns_names:
        return dns_names
    return None


def compare_cloud_id_or_hostname(adapter_device1, adapter_device2):
    cloud_id_or_hostname_1 = get_cloud_id_or_hostname(adapter_device1)
    cloud_id_or_hostname_2 = get_cloud_id_or_hostname(adapter_device2)
    if cloud_id_or_hostname_1 and cloud_id_or_hostname_2:
        return cloud_id_or_hostname_1 == cloud_id_or_hostname_2
    return True


def is_azuread_or_ad_and_have_name(adapter_device):
    # Its from ad or azuread and it also has one of these fields not None.
    return adapter_device.get('plugin_name') in ('active_directory_adapter', 'azure_ad_adapter') and \
        get_ad_name_or_azure_display_name(adapter_device)


def is_from_no_mac_adapters_with_empty_mac(adapter_device):
    return (adapter_device['plugin_name'] in ['epo_adapter', 'observeit_adapter', 'cynet_adapter']) and \
           (not adapter_device.get(NORMALIZED_MACS))


def is_from_ad(adapter_device):
    return adapter_device.get('plugin_name') == 'active_directory_adapter'


def get_azure_ad_id(adapter_device):
    azure_ad_id = adapter_device.get('data').get('azure_ad_id') or adapter_device.get('data').get('azure_device_id')
    if azure_ad_id != '00000000-0000-0000-0000-000000000000':
        return azure_ad_id
    return None


def compare_azure_ad_id(adapter_device1, adapter_device2):
    azure_ad_id_1 = get_azure_ad_id(adapter_device1)
    azure_ad_id_2 = get_azure_ad_id(adapter_device2)
    if azure_ad_id_1 and azure_ad_id_2:
        return azure_ad_id_1 == azure_ad_id_2
    return False


def is_from_azure_ad(adapter_device):
    return adapter_device.get('plugin_name') == 'azure_ad_adapter'


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
    return adapter_device.get('plugin_name') in ['juniper_adapter', 'junos_adapter'] and \
        adapter_device.get('data', {}).get('name')


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


def is_windows(adapter_device):
    os_type = get_os_type(adapter_device)
    if not os_type:
        return False
    if os_type.lower() == 'windows':
        return True
    return False


def get_id(adapter_device):
    return adapter_device['data'].get('id')


def get_hostname(adapter_device):
    return adapter_device['data'].get('hostname')


def calculate_normalized_hostname(adapter_device) -> str:
    hostname = get_hostname(adapter_device)
    if hostname:
        splitted = hostname.split('.')
        if splitted:
            return splitted[0].lower()
    return None


def get_hostname_no_localhost(adapter_device):
    if not get_hostname(adapter_device):
        return None
    if get_hostname(adapter_device).split('.')[0].lower() == 'localhost':
        return None
    return get_hostname(adapter_device)


def get_nessus_no_scan_id(adapter_device):
    nessus_no_scan_id = adapter_device['data'].get('nessus_no_scan_id')
    if nessus_no_scan_id:
        return nessus_no_scan_id.lower()
    return None


def compare_nessus_no_scan_id(adapter_device1, adapter_device2):
    nessus_no_scan_id_1 = get_nessus_no_scan_id(adapter_device1)
    nessus_no_scan_id_2 = get_nessus_no_scan_id(adapter_device2)
    if nessus_no_scan_id_1 and nessus_no_scan_id_2 and nessus_no_scan_id_1 == nessus_no_scan_id_2:
        return True
    return False


def get_domain(adapter_device):
    domain = adapter_device['data'].get('domain')
    if domain and is_domain_valid(domain):
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
    def normalize_users_list(users_list):
        return [normalize_username(username) for username in users_list
                if (normalize_username(username) and 'admin' not in username.lower() and 'user' not in username.lower()
                    and 'guest' not in username.lower() and 'root' not in username.lower()
                    and not username.lower().startswith('_') and 'nobody' not in username.lower()
                    and '-svc' not in username.lower())]
    users1 = get_last_used_users(adapter_device1)
    users2 = get_last_used_users(adapter_device2)
    if not users1 or not users2:
        return False
    users1 = normalize_users_list(users1)
    users2 = normalize_users_list(users2)
    if not users1 or not users2:
        return False
    return is_items_in_list1_are_in_list2(users1, users2) or is_items_in_list1_are_in_list2(users2, users1)


def get_uuid(adapter_device):
    uuid = adapter_device['data'].get('uuid')
    if uuid and str(uuid).lower() not in ['none', 'n/a', '0', 'unknown', 'undefined']:
        return uuid.lower()
    return None


def compare_uuid(adapter_device1, adapter_device2):
    uuid1 = get_uuid(adapter_device1)
    uuid2 = get_uuid(adapter_device2)
    if uuid1 and uuid2 and uuid1 == uuid2:
        return True
    return False


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
        if name.endswith('$'):
            name = name[:-1]
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
        if serial and serial.upper().strip().replace(' ', '') in BAD_SERIALS:
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


def is_epo_adapter(adapter_device):
    return adapter_device.get('plugin_name') == 'epo_adapter'


def get_asset_name(adapter_device):
    if adapter_device['data'].get('name') and not is_qualys_adapter(adapter_device) \
            and (not is_bluecat_adapter(adapter_device) or not adapter_device.get(NORMALIZED_MACS)) \
            and not is_tenable_io_adapter(adapter_device) \
            and not is_epo_adapter(adapter_device) \
            and not is_g_naapi_adapter(adapter_device):
        asset = adapter_device['data'].get('name').upper().strip()
        if asset not in ['UNKNOWN']:
            return asset
    return None


def get_serial(adapter_device):
    serial = (adapter_device['data'].get('device_serial') or '').strip()
    if serial \
            and serial.upper().strip().replace(' ', '') not in BAD_SERIALS \
            and 'VMWARE' not in serial.upper().strip():
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


def is_start_with_valid_ip(value):
    if not value or not value.strip():
        return False
    value = value.strip()
    value = value.split('_')[0].split('-')[0].split(',')[0].split(' ')[0]
    return is_valid_ip(value)


BAD_ASSETS = ['dev', 'localhost', 'delete', 'deleted', 'na', 'macbook-air',
              'unknown', 'test1', 'stage', 'ipad', 'iphone']


def is_asset_before_host_device(adapter_device):
    if adapter_device.get('plugin_name') in ['service_now_adapter', 'gce_adapter']:
        return True
    return False


def get_asset_snow_or_host(adapter_device):
    if is_asset_before_host_device(adapter_device):
        asset = get_asset_name(adapter_device)
    else:
        asset = get_hostname(adapter_device)
    if asset:
        if is_start_with_valid_ip(asset) or ' ' in asset or asset.split('.')[0].lower().strip() in BAD_ASSETS:
            return asset
        return asset.split('.')[0].lower().strip()
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
        if is_start_with_valid_ip(asset) or ' ' in asset or asset.split('.')[0].lower().strip() in BAD_ASSETS:
            return asset
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
        return cloud_provider.upper().strip() + '-' + cloud_id.upper().strip()

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
        if is_valid_ip(final_hostname):
            split_hostname = [final_hostname]
        else:
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
        return host1 and host2 and host1[0] == host2[0]


def have_mac_intersection(adapter_device1, adapter_device2) -> bool:
    """
    In these case we are looking for mac intersections. We do that in cases where hostname are equals,
    but IPs contradict. This can happens for various reasons at agents. If we have some mac which is equals,
    this is enough for correlation
    :param adapter_device1:
    :param adapter_device2:
    :return Whether there is at least one mac in both adapter_devices:
    """
    device1_macs = set(adapter_device1.get(NORMALIZED_MACS) or []).union(
        set([normalize_mac(mac_raw) for mac_raw in (adapter_device1['data'].get('macs_no_ip') or [])]))
    device2_macs = set(adapter_device2.get(NORMALIZED_MACS) or []).union(
        set([normalize_mac(mac_raw)for mac_raw in (adapter_device2['data'].get('macs_no_ip') or [])]))
    return bool(device1_macs.intersection(device2_macs))


def ips_do_not_contradict_or_mac_intersection(adapter_device1, adapter_device2):
    return (ips_do_not_contradict(adapter_device1, adapter_device2) and get_normalized_ip(adapter_device1) and get_normalized_ip(adapter_device2)) or have_mac_intersection(adapter_device1, adapter_device2)


def ips_do_not_contradict(adapter_device1, adapter_device2):
    device1_ips = adapter_device1.get(NORMALIZED_IPS)
    device2_ips = adapter_device2.get(NORMALIZED_IPS)
    device1_ips_v4 = adapter_device1.get(NORMALIZED_IPS_4)
    device2_ips_v4 = adapter_device2.get(NORMALIZED_IPS_4)
    return not device1_ips or not device2_ips or is_one_subset_of_the_other(device1_ips, device2_ips) or (device1_ips_v4 and device2_ips_v4 and is_one_subset_of_the_other(device1_ips_v4, device2_ips_v4))


def macs_do_not_contradict(adapter_device1, adapter_device2):
    if (adapter_device1.get('plugin_name') == 'jamf_adapter' and
        adapter_device2.get('plugin_name') == 'carbonblack_defense_adapter') \
        or (adapter_device2.get('plugin_name') == 'jamf_adapter' and
            adapter_device1.get('plugin_name') == 'carbonblack_defense_adapter'):
        return True
    device1_macs = adapter_device1.get(NORMALIZED_MACS)
    device2_macs = adapter_device2.get(NORMALIZED_MACS)
    return not device1_macs or not device2_macs or have_mac_intersection(adapter_device1, adapter_device2)


def not_snow_adapters(adapter_device1, adapter_device2):
    return not is_snow_adapter(adapter_device1) and not is_snow_adapter(adapter_device2)


def not_airwatch_adapters(adapter_device1, adapter_device2):
    return not is_airwtch_adapter(adapter_device1) and not is_airwtch_adapter(adapter_device2)


def dangerous_asset_names_do_not_contradict(adapter_device1, adapter_device2):
    if is_dangerous_asset_names_adapter(adapter_device1) and is_dangerous_asset_names_adapter(adapter_device2):
        asset1 = get_asset_name(adapter_device1)
        asset2 = get_asset_name(adapter_device2)
        if asset1 and asset2 and asset1.lower() != asset2.lower():
            return False
    elif not is_dangerous_asset_names_adapter(adapter_device1)\
            and not is_dangerous_asset_names_adapter(adapter_device2):
        return True
    else:
        if is_dangerous_asset_names_adapter(adapter_device1):
            asset1 = get_asset_name(adapter_device1)
            asset2 = get_hostname(adapter_device2)
            if asset1 and asset2:
                asset1_lower = asset1.split('.')[0].lower().strip('e').strip('g').split('_')[0]
                asset2_lower = asset2.split('.')[0].lower().strip('e').strip('g').split('_')[0]
                if asset1_lower in asset2_lower or asset2_lower in asset1_lower:
                    return True
                return False
        if is_dangerous_asset_names_adapter(adapter_device2):
            asset1 = get_hostname(adapter_device1)
            asset2 = get_asset_name(adapter_device2)
            if asset1 and asset2:
                asset1_lower = asset1.split('.')[0].lower().strip('e').strip('g').split('_')[0]
                asset2_lower = asset2.split('.')[0].lower().strip('e').strip('g').split('_')[0]
                if asset1_lower in asset2_lower or asset2_lower in asset1_lower:
                    return True
                return False
    return True


def asset_hostnames_do_not_contradict(adapter_device1, adapter_device2):
    return hostnames_do_not_contradict(adapter_device1, adapter_device2) and \
        dangerous_asset_names_do_not_contradict(adapter_device1, adapter_device2)


def serials_do_not_contradict(adapter_device1, adapter_device2):
    serial1 = get_serial(adapter_device1)
    serial2 = get_serial(adapter_device2)
    if not serial1 or not serial2:
        return True
    return serial1 == serial2


def is_freshservice_adapter(adapter_device):
    return adapter_device.get('plugin_name') == 'fresh_service_adapter'


def hostnames_do_not_contradict(adapter_device1, adapter_device2):
    if not get_hostname(adapter_device1) or not get_hostname(adapter_device2) \
            or is_freshservice_adapter(adapter_device1) or is_freshservice_adapter(adapter_device2):
        return True
    return compare_device_normalized_hostname(adapter_device1, adapter_device2)


def os_do_not_contradict(adapter_device1, adapter_device2):
    if not get_os_type(adapter_device1) or not get_os_type(adapter_device2):
        return True
    return get_os_type(adapter_device1) == get_os_type(adapter_device2)


def not_contain_generic_jamf_names(adapter_device1, adapter_device2):
    return not contain_jamf_generic_names(adapter_device1) or not contain_jamf_generic_names(adapter_device2)


def contain_jamf_generic_names(adapter_device):
    hostname = get_hostname(adapter_device)
    if not hostname:
        return False
    if 'MacBook' in hostname or 'MBP' in hostname or 'localhost' in hostname or\
            'iPad' in hostname or 'iPhone' in hostname or 'iMac' in hostname or 'mini' in hostname\
            or 'Mac-mini' in hostname or 'Tests-MacBook-Pro' in hostname \
            or 'loaner' in hostname or 'blank' in hostname or 'MacBook-Air' in hostname:
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


def compare_full_mac(adapter_device1, adapter_device2):
    first_set = adapter_device1.get(NORMALIZED_MACS)
    second_set = adapter_device2.get(NORMALIZED_MACS)
    return first_set.issubset(second_set) and second_set.issubset(first_set)


def compare_macs(adapter_device1, adapter_device2):
    return is_one_subset_of_the_other(adapter_device1.get(NORMALIZED_MACS), adapter_device2.get(NORMALIZED_MACS))


def compare_dns_names(adapter_device1, adapter_device2):
    ad1_dns_names = adapter_device1['data'].get('dns_names')
    ad2_dns_names = adapter_device2['data'].get('dns_names')
    if not isinstance(ad1_dns_names, list) or not isinstance(ad2_dns_names, list):
        return False
    ad1_dns_names = set(dns_name.upper() for dns_name in ad1_dns_names)
    ad2_dns_names = set(dns_name.upper() for dns_name in ad2_dns_names)
    return is_one_subset_of_the_other(ad1_dns_names, ad2_dns_names)


def compare_device_normalized_hostname(adapter_device1, adapter_device2) -> bool:
    """
    See compare_normalized_hostnames docs
    :param adapter_device1: first device
    :param adapter_device2: second device
    :return:
    """
    def is_in_short_names_adapters_and_long_name(adapter_device):
        if is_linux(adapter_device):
            return False
        if adapter_device.get('plugin_name') in ['carbonblack_protection_adapter',
                                                 'active_directory_adapter',
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
        if len(ips) > 0:
            adapter_device[NORMALIZED_IPS_4] = set([ip for ip in ips if is_valid_ipv4(ip)])
            adapter_device[NORMALIZED_IPS_6] = set([ip for ip in ips if is_valid_ipv6(ip)])
        adapter_device[NORMALIZED_MACS] = macs if len(macs) > 0 else None
    # Save the normalized hostname so we can later easily compare.
    # See further doc near definition of NORMALIZED_HOSTNAME.
    adapter_device[NORMALIZED_HOSTNAME] = normalize_hostname(adapter_data)
    if adapter_device[NORMALIZED_HOSTNAME]:
        adapter_device[NORMALIZED_HOSTNAME_STRING] = '.'.join(adapter_device[NORMALIZED_HOSTNAME]) + '.'
    if not adapter_device.get(NORMALIZED_HOSTNAME_STRING) and \
            is_from_azure_ad(adapter_device) and get_asset_name(adapter_device):
        adapter_device[NORMALIZED_HOSTNAME_STRING] = get_asset_name(adapter_device)
        adapter_device[NORMALIZED_HOSTNAME] = [get_asset_name(adapter_device)]
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


def make_dict_from_csv(csv_data) -> csv.DictReader:
    return csv.DictReader(csv_data.splitlines(), dialect=csv.Sniffer().sniff(csv_data.splitlines()[0],
                                                                             delimiters=[';', ',', '\t']))


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


def int_to_mac(macint):
    if type(macint) != int:
        raise ValueError('invalid integer')
    return ':'.join(['{}{}'.format(a, b) for a, b in zip(*[iter('{:012x}'.format(macint))] * 2)])


def remove_large_ints(data, name: str):
    """
    Go over a dict and remove any number which is larger than 8 bytes, since MongoDB can't eat it.
    :param data: the
    """
    if isinstance(data, int) and data > BSON_SPEC_MAX_INT:
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


def replace_large_ints(data):
    """
    Go over a dict and replace any number which is larger than 8 bytes with str, since MongoDB can't eat it.
    :param data: the
    """
    if isinstance(data, int):
        if data > BSON_SPEC_MAX_INT:
            return str(data)
        return data

    if isinstance(data, dict):
        new_dict = dict()
        for key, value in data.items():
            new_value = replace_large_ints(value)
            new_dict[key] = new_value

        return new_dict

    if isinstance(data, list):
        new_list = []
        for i, value in enumerate(data):
            new_value = replace_large_ints(value)
            new_list.append(new_value)

        return new_list

    return data
