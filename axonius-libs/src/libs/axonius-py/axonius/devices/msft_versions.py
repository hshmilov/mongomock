"""
https://axonius.atlassian.net/browse/PROD-1223

parse MSFT release version ( NT XX.XX ) format to windows version format (i.e Server 2019, Server 2012 R2 ,10, 8.1 XP)

sample :  Windows NT Workstation 5.1  -- >  XP
"""
import re


WINDOWS_VERSION_REGEX = r'\d+(?:\.\d+)+'

WORKSTATION_VERSIONS = {
    '4.0': '95',
    '4.1': '98',
    '4.9': 'Me',
    '5.0': '2000',
    '5.1': 'XP',
    '5.2': 'XP Professional x64 Edition',
    '6.0': 'Vista',
    '6.1': '7',
    '6.2': '8',
    '6.3': '8.1',
    '10.0': '10'
}

SERVER_VERSIONS = {
    '4.0': 'NT',
    '5.0': 'Server 2000',
    '5.2': 'Server 2003',
    '6.0': 'Server 2008',
    '6.1': 'Server 2008 R2',
    '6.2': 'Server 2012',
    '6.3': 'Server 2012 R2',
    '10.0': {'14393': 'Server 2016',
             'default': 'Server 2019'}
}

SERVER_YEARS = ['2003', '2008', '2012', '2016', '2019']

ENUM_WINDOWS_VERSIONS = ['Server 2019',
                         'Server 2016',
                         '10',
                         'Server 2012 R2',
                         '8.1',
                         '8',
                         'Server 2012',
                         'Server 2008 R2',
                         '7',
                         'Server 2008',
                         'Vista',
                         'XP Professional x64 Edition',
                         'Server 2003',
                         'XP',
                         'Me',
                         'Server 2000',
                         '2000',
                         '98',
                         'NT',
                         '95']


def parse_msft_release_version(os_string):

    versions = SERVER_VERSIONS if 'server' in os_string or any(x in os_string for x in SERVER_YEARS)\
        else WORKSTATION_VERSIONS
    for rls_ver, win_ver in versions.items():
        matched_version = re.findall(WINDOWS_VERSION_REGEX, os_string)
        if matched_version and matched_version[0].startswith(rls_ver):
            if isinstance(win_ver, dict):
                if '2016' in os_string or '2019' in os_string:
                    return None
                for build, ver in win_ver.items():
                    return ver if build in os_string else win_ver.get('default')
            return win_ver
    return None
