"""
ParsingUtils.py: Collection of utils that might be used by parsers, specifically adapters
"""

import re
import sys
from types import FunctionType
from typing import NewType, Callable
from axonius.entities import EntityType

import dateutil.parser
import ipaddress
import binascii
import base64
import datetime
import pql
import csv

osx_version_fallback = re.compile(r'[^\w](\d+\.\d+.\d+)')
osx_version = re.compile(r'[^\w](\d+\.\d+.\d+)[^\w]')
osx_version_full = re.compile(r'[^\w](\d+\.\d+.\d+)\s*(\(\w+\))')
ubuntu_full = re.compile(r'([Uu]buntu \d\d\.\d\d(?:\.\d+)?)')
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
DEFAULT_DOMAIN_EXTENSIONS = ['.LOCAL', '.WORKGROUP']
# NORMALIZED_IPS/MACS fields will hold the set of IPs and MACs an adapter devices has extracted.
# Without it, in order to compare IPs and MACs we would have to go through the list of network interfaces and extract
# them each time.
NORMALIZED_IPS = 'normalized_ips'
NORMALIZED_MACS = 'normalized_macs'

pair_comparator = NewType('lambda x,y -> bool', FunctionType)
parameter_function = NewType('lambda x -> paramter of x', Callable)


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
    s = s.strip().lower()

    makes_64bit = ['amd64', '64-bit', 'x64', '64 bit', 'x86_64']
    makes_32bit = ['32-bit', 'x86']

    bitness = None
    if any(x in s for x in makes_64bit):
        bitness = 64
    elif any(x in s for x in makes_32bit):
        bitness = 32

    os_type = None
    distribution = None
    linux_names = ["linux", 'ubuntu', 'canonical', 'red hat',
                   'debian', 'fedora', 'centos', 'oracle', 'opensuse']

    ios_names = ["iphone", "ipad", "ios", "apple"]

    if 'windows' in s or 'win' in s:
        os_type = 'Windows'
        windows_distribution = ['Vista', 'XP', 'Windows 7', 'Windows 8', 'Windows 8.1', 'Windows 10',
                                'Windows Server 2003', 'Win10', 'Win7', 'Win8', 'Windows 2016',
                                'Windows 2008', 'Windows 2012',
                                'Windows Server 2008', 'Windows Server 2012', 'Windows Server 2016']
        for dist in windows_distribution:
            if dist.lower() in s:
                distribution = dist.replace("Windows ", "").replace("Win", "")
                break

    elif any(x in s for x in linux_names):
        os_type = 'Linux'
        linux_distributions = [ubuntu_full, "Ubuntu", "Red Hat", "Debian", "Fedora"]
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
    elif 'os x' in s or 'osx' in s:
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
    elif 'android' in s:
        os_type = 'Android'
        version = mobile_version.findall(s)
        if len(version):
            distribution = version[0]
    elif 'freebsd' in s:
        os_type = "FreeBSD"
        distribution = "FreeBSD"
    elif 'Junos OS' in s:
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

    elif 'cisco' in s.lower():
        os_type = 'Cisco'

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


def get_first_object_from_dn(dn):
    """
    :param dn: e.g. CN=Administrator,CN=Users,DC=TestDomain,DC=test
    :return: e.g. Administrator
    """
    if type(dn) == str:
        dn = dn.split(",")
        if len(dn) > 0:
            # This usually looks like CN=User Name, CN=Users, DC=.... so lets take the first one
            rv = dn[0].split("=")
            if len(rv) == 2:
                return rv[1]

    return None


def get_member_of_list_from_memberof(member_of):
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
    # convert mac in canonical form (eg. 00:80:41:ae:fd:7e)
    mac = ":".join(["%s" % (mac[i:i + 2]) for i in range(0, 12, 2)])
    return mac.upper()


def format_ip(value):
    try:
        return str(ipaddress.ip_address(value))
    except Exception:
        raise ValueError(f'Invalid IP address: {value}')


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
        else:
            raise ValueError(f"Invalid image. header is {header}, cannot determine if jpeg/png/gif.")
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


def is_date_real(datetime_to_parse):
    """
    Often we might encounter a situation where a datetime is valid, but actually represents
    an empty value. for that case we have this function.
    :param datetime_to_parse: 
    :return: True if real, False otherwise.
    """

    # 1/1/1970 - Unix epoch
    # 1/1/1601 - Windows NT epoch(The FILETIME structure records time in the form
    #            of 100-nanosecond intervals since January 1, 1601.)

    return type(datetime_to_parse) == datetime.datetime and \
        datetime_to_parse.replace(tzinfo=None) != datetime.datetime(1601, 1, 1) and \
        datetime_to_parse.replace(tzinfo=None) != datetime.datetime(1970, 1, 1)


def parse_date(datetime_to_parse):
    try:
        if type(datetime_to_parse) == datetime.datetime:
            # sometimes that happens too
            return datetime_to_parse
        d = dateutil.parser.parse(datetime_to_parse, ignoretz=True)

        # Sometimes, this would be a fake date (see is_date_real). in this case return None
        return d if is_date_real(d) else None
    except (TypeError, ValueError):
        return None


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
            yield current_mac.upper().replace('-', '').replace(':', '')


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
    return adapter_device1['data']['hostname'] == adapter_device2['data']['hostname']


def is_a_scanner(adapter_device):
    """
    checks if the adapters is the result of a scanner device
    :param adapter_device: an adapter device to check
    """
    from axonius.devices.device_adapter import SCANNER_FIELD
    if adapter_device['data'].get(SCANNER_FIELD, False):
        return True
    return False


def is_different_plugin(adapter_device1, adapter_device2):
    return adapter_device1['plugin_name'] != adapter_device2['plugin_name']


def is_from_ad(adapter_device):
    return adapter_device['plugin_name'] == 'active_directory_adapter'


def get_os_type(adapter_device):
    from axonius.devices.device_adapter import OS_FIELD
    return (adapter_device['data'].get(OS_FIELD) or {}).get('type')


def get_hostname(adapter_device):
    return adapter_device['data'].get('hostname')


def get_serial(adapter_device):
    return adapter_device['data'].get('device_serial')


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
        for extension in DEFAULT_DOMAIN_EXTENSIONS:
            final_hostname = remove_trailing(final_hostname, extension)
        return final_hostname.split('.')


def compare_normalized_hostnames(host1, host2) -> bool:
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
    return host1 and host2 and (does_list_startswith(host1, host2) or
                                does_list_startswith(host2, host1))


def ips_do_not_contradict(adapter_device1, adapter_device2):
    device1_ips = adapter_device1.get(NORMALIZED_IPS)
    device2_ips = adapter_device2.get(NORMALIZED_IPS)
    return not device1_ips or not device2_ips or is_one_subset_of_the_other(device1_ips, device2_ips)


def macs_do_not_contradict(adapter_device1, adapter_device2):
    device1_macs = adapter_device1.get(NORMALIZED_MACS)
    device2_macs = adapter_device2.get(NORMALIZED_MACS)
    return not device1_macs or not device2_macs or is_one_subset_of_the_other(device1_macs, device2_macs)


def hostnames_do_not_contradict(adapter_device1, adapter_device2):
    device1_hostnames = adapter_device1.get(NORMALIZED_HOSTNAME)
    device2_hostnames = adapter_device2.get(NORMALIZED_HOSTNAME)
    return not device1_hostnames or not device2_hostnames or compare_normalized_hostnames(device1_hostnames,
                                                                                          device2_hostnames)


def compare_ips(adapter_device1, adapter_device2):
    return is_one_subset_of_the_other(adapter_device1.get(NORMALIZED_IPS), adapter_device2.get(NORMALIZED_IPS))


def compare_macs(adapter_device1, adapter_device2):
    return is_one_subset_of_the_other(adapter_device1.get(NORMALIZED_MACS), adapter_device2.get(NORMALIZED_MACS))


def compare_device_normalized_hostname(adapter_device1, adapter_device2) -> bool:
    """
    See compare_normalized_hostnames docs
    :param adapter_device1: first device
    :param adapter_device2: second device
    :return:
    """
    return compare_normalized_hostnames(adapter_device1.get(NORMALIZED_HOSTNAME),
                                        adapter_device2.get(NORMALIZED_HOSTNAME))


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


def parse_filter(filter):
    """
    Translates a string representing
    :param filter:
    :return:
    """
    matches = re.search('NOW\s*-\s*(\d+)([hdw])', filter)
    if not matches:
        return pql.find(filter)

    # Handle predefined sequence that should be replaced before translation
    computed_date = datetime.datetime.now()
    if matches.group(2) == 'h':
        computed_date -= datetime.timedelta(hours=int(matches.group(1)))
    elif matches.group(2) == 'd':
        computed_date -= datetime.timedelta(days=int(matches.group(1)))
    elif matches.group(2) == 'w':
        computed_date -= datetime.timedelta(days=int(matches.group(1)) * 7)
    return pql.find(filter.replace(matches.group(0), computed_date.strftime("%m/%d/%Y %I:%M %p")))


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


def make_dict_from_csv(csv_data):
    return csv.DictReader(csv_data.splitlines(), dialect=csv.Sniffer().sniff(csv_data[:1024]))
