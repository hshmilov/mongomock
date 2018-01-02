"""
ParsingUtils.py: Collection of utils that might be used by parsers, specifically adapters
"""

__author__ = "Mark Segal"

import codenamize
import re


osx_version = re.compile(r'[^\w](\d+\.\d+.\d+)[^\w]')
osx_version_full = re.compile(r'[^\w](\d+\.\d+.\d+)\s*(\(\w+\))')
ubuntu_full = re.compile(r'([Uu]buntu \d\d\.\d\d(?:\.\d+)?)')
mobile_version = re.compile(r'(\d+\.\d+.\d+)')


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

    return {"type": os_type,
            "distribution": distribution,
            "bitness": bitness}


def beautiful_adapter_device_name(adapter_plugin_name: str, adapter_device_id: str):
    """
    Produces a human memorizable name for a device
    :param adapter_plugin_name: The plugin name for the adapter that found this device
    :param adapter_device_id: The device ID as provided by the adapter
    :return: str
    """
    return codenamize.codenamize(f"{adapter_plugin_name}->{adapter_device_id}", adjectives=3, max_item_chars=10)


def format_mac(mac: str) -> str:
    mac = re.sub('[.:-]', '', mac).lower()  # remove delimiters and convert to lower case
    mac = ''.join(mac.split())  # remove whitespaces
    assert len(mac) == 12  # length should be now exactly 12 (eg. 008041aefd7e)
    assert mac.isalnum()  # should only contain letters and numbers
    # convert mac in canonical form (eg. 00:80:41:ae:fd:7e)
    mac = ":".join(["%s" % (mac[i:i + 2]) for i in range(0, 12, 2)])
    return mac.upper()
