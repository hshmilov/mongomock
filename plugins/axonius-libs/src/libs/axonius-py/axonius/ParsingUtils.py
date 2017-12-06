"""
ParsingUtils.py: Collection of utils that might be used by parsers, specifically adapters
"""

__author__ = "Mark Segal"

import codenamize


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
    s = s.lower()

    makes_64bit = ['amd64', '64-bit', 'x64']
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
        linux_distributions = ["Ubuntu", "Red Hat", "Debian", "Fedora"]
        for dist in linux_distributions:
            if dist.lower() in s:
                distribution = dist
                break
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
