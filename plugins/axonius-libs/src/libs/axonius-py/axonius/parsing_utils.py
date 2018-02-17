"""
ParsingUtils.py: Collection of utils that might be used by parsers, specifically adapters
"""

__author__ = "Mark Segal"

import re
import sys
import os
import dateutil.parser
import ipaddress
from bson.decimal128 import Decimal128, create_decimal128_context
import decimal

osx_version = re.compile(r'[^\w](\d+\.\d+.\d+)[^\w]')
osx_version_full = re.compile(r'[^\w](\d+\.\d+.\d+)\s*(\(\w+\))')
ubuntu_full = re.compile(r'([Uu]buntu \d\d\.\d\d(?:\.\d+)?)')
mobile_version = re.compile(r'(\d+\.\d+.\d+)')


def get_exception_string():
    """
    when inside a catch exception flow, returns a really informative string representing it.
    :return: a string representing the exception.
    """

    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    return "{0}:{1}, in location {2}:{3}".format(exc_type, exc_obj, fname, exc_tb.tb_lineno)


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
    s = s.lower()

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

    ios_names = ["iphone", "ipad"]

    if 'windows' in s:
        os_type = 'Windows'
        windows_distribution = ['Vista', 'XP', 'Windows 7', 'Windows 8', 'Windows 8.1', 'Windows 10',
                                'Windows Server 2003',
                                'Windows Server 2008', 'Windows Server 2012', 'Windows Server 2016']
        for dist in windows_distribution:
            if dist.lower() in s:
                distribution = dist.replace("Windows ", "")
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
    elif 'os x' in s:
        os_type = 'OS X'
        version = osx_version_full.findall(s)
        if len(version) > 0:
            distribution = ' '.join(version[0])
        else:
            version = osx_version.findall(s)
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

    return {"type": os_type,
            "distribution": distribution,
            "bitness": bitness}


def is_valid_ip(ip):
    try:
        ipaddress.ip_address(ip)
        return True
    except:
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
    except:
        raise ValueError(f'Invalid IP address: {value}')


def format_ip_raw(value):
    try:
        address = ipaddress.ip_address(value)
        if isinstance(address, ipaddress.IPv4Address):
            return address._ip
        return None
        # TODO: Add support to ipv6
        #decimal128_ctx = create_decimal128_context()
        # with decimal.localcontext(decimal128_ctx) as ctx:
        # return Decimal128(ctx.create_decimal(str(address._ip)))
    except:
        raise ValueError(f'Invalid raw IP address: {value}')


def parse_date(datetime_as_string):
    try:
        return dateutil.parser.parse(datetime_as_string, ignoretz=True)
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


def get_device_id_for_plugin_name(associated_adapter_devices, plugin_name_key):
    """
    iterates over associated_adapter_devices and returns the device_id of the device info returned from
        plugin_name_key or None if plugin_name_key is not one of the adapters which returned info on the device
    :param associated_adapter_devices: the adapters containing all the info of the device
    :param plugin_name_key: the plugin_unique_name for which to seek the device id
    """
    return next((device_id for plugin_unique_name, device_id in associated_adapter_devices
                 if plugin_name_key == plugin_unique_name), None)
