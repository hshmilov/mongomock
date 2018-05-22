# from ldap_connection import LdapConnection
import json
import subprocess
import time
import pytest
import os
from active_directory_adapter.ldap_connection import LdapConnection, SSLState
from testing.test_credentials.test_ad_credentials import ad_client1_details, PM_DEVICE_ADDRESS
from axonius.utils.parsing import ad_integer8_to_timedelta
from datetime import timedelta

USERNAME = ad_client1_details["user"]
PASSWORD = ad_client1_details["password"]
ADDRESS = ad_client1_details["dc_name"]

ACCOUNTDISABLE = 0x0002

WMI_SMB_RUNNER_LOCATION = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "axonius-libs", "src", "libs", "axonius-py", "axonius",
                 "utils", "wmi_smb_runner", "wmi_smb_runner.py"))

TEST_BINARY_LOCATION = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "tests", "test_binary", "test_binary.exe"))

AXPM_BINARY_LOCATION = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..",
                 "shared_readonly_files", "AXPM", "AXPM.exe"))

WSUSSCN2_BINARY_LOCATION = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..",
                 "shared_readonly_files", "AXPM", "wsusscn2", "wsusscn2.cab"))


@pytest.fixture(scope="module")
def ldap_connection():
    return LdapConnection(900, ADDRESS, USERNAME,
                          PASSWORD, None, SSLState[SSLState.Unencrypted.name], bytes([]), bytes([]),
                          bytes([]), True, True)


def test_users(ldap_connection: LdapConnection):
    users = list(ldap_connection.get_users_list())

    users_dict = {}
    has_disabled_user = False
    for user in users:
        users_dict[user["sAMAccountName"]] = user
        if user["userAccountControl"] & ACCOUNTDISABLE > 0:
            has_disabled_user = True

    assert len(users_dict) > 0
    assert users_dict['avidor']['cn'] == 'Avidor Bartov'
    assert users_dict['Administrator']['adminCount'] == 1
    assert "maxPwdAge" in users_dict['avidor']['axonius_extended']

    # assert there is at least one disabled device
    assert has_disabled_user is True


def test_devices(ldap_connection: LdapConnection):
    devices = ldap_connection.get_device_list()
    devices_dict = {}
    has_disabled_device = True
    for device in devices:
        devices_dict[device['distinguishedName']] = device
        if device["userAccountControl"] & ACCOUNTDISABLE > 0:
            has_disabled_device = True

    assert len(devices_dict) > 0

    test_device = devices_dict["CN=DESKTOP-MPP10U1,CN=Computers,DC=TestDomain,DC=test"]
    assert test_device["name"] == "DESKTOP-MPP10U1"
    assert test_device["operatingSystem"] == "Windows 10 Pro"

    # assert there is at least one disabled device
    assert has_disabled_device is True


@pytest.mark.skip("printer is gone, need to fix")
def test_printers(ldap_connection: LdapConnection):
    printers = ldap_connection.get_printers_list()
    printers_dict = {}
    for printer in printers:
        printers_dict[printer['distinguishedName']] = printer

    assert len(printers_dict) > 0

    test_printer = printers_dict["CN=DESKTOP-MPP10U1-AXONIUS-OFFICE-PRINTER (HP Color LaserJet MF,CN=DESKTOP-MPP10U1,"
                                 "CN=Computers,DC=TestDomain,DC=test"]
    assert test_printer["serverName"] == "DESKTOP-MPP10U1.TestDomain.test"


def test_get_fsmo_roles(ldap_connection: LdapConnection):
    fsmo_dict = ldap_connection.get_fsmo_roles()
    assert fsmo_dict['pdc_emulator'] == 'dc1.TestDomain.test'
    assert fsmo_dict['rid_master'] == 'dc1.TestDomain.test'
    assert fsmo_dict['infra_master'] == 'dc1.TestDomain.test'
    assert fsmo_dict['naming_master'] == 'dc1.TestDomain.test'
    assert fsmo_dict['schema_master'] == 'dc1.TestDomain.test'


def test_get_global_catalogs(ldap_connection: LdapConnection):
    global_catalogs = ldap_connection.get_global_catalogs()
    assert "dc1.TestDomain.test" in global_catalogs
    assert "raindc1.raindomain.test" in global_catalogs


def test_get_dhcp_servers(ldap_connection: LdapConnection):
    dhcp_servers = ldap_connection.get_dhcp_servers()
    assert "dc2.testdomain.test" in dhcp_servers


def test_get_domain_properties(ldap_connection: LdapConnection):
    domain_properties = ldap_connection.get_domain_properties()
    assert "maxPwdAge" in domain_properties
    assert domain_properties['name'] == 'TestDomain'
    assert ad_integer8_to_timedelta(domain_properties["maxPwdAge"]) == timedelta(days=999)


def test_get_dc_properties(ldap_connection: LdapConnection):
    dc_properties = ldap_connection.get_dc_properties()
    assert dc_properties['defaultNamingContext'] == ['DC=TestDomain,DC=test']
    assert dc_properties['configurationNamingContext'] == ['CN=Configuration,DC=TestDomain,DC=test']


def test_get_dns_records(ldap_connection: LdapConnection):
    dns_records = list(ldap_connection.get_dns_records())
    assert ("dc", "192.168.20.25") in dns_records
    assert ("DESKTOP-MPP10U1", "fc3b:db8:85a3:42:1000:8a2e:370:7334") in dns_records

    only_one_dns_record = list(ldap_connection.get_dns_records("dc1"))
    assert len(only_one_dns_record) == 1
    assert ("dc1", "192.168.20.25") in only_one_dns_record


def test_get_sites(ldap_connection: LdapConnection):
    sites = ldap_connection.get_sites()
    sites_dict = {}
    for site in sites:
        sites_dict[site['name']] = site

    assert 'TestDomain-TelAviv' in sites_dict
    assert 'CN=192.168.20.0/24,CN=Subnets,CN=Sites,CN=Configuration,DC=TestDomain,DC=test' in sites_dict[
        'TestDomain-TelAviv']['siteObjectBL']


def test_get_subnets(ldap_connection: LdapConnection):
    subnets = ldap_connection.get_subnets()
    subnets_dict = {}
    for subnet in subnets:
        subnets_dict[subnet['name']] = subnet

    assert '10.0.2.0/24' in subnets_dict
    assert subnets_dict['10.0.2.0/24']['description'] == ['Office Private Subnet']
    assert subnets_dict['10.0.2.0/24']['location'] == "New York"


def test_get_dfsr_shares(ldap_connection: LdapConnection):
    dfsr_shares_dict = {}
    for dfsr_replication_group_name, dfsr_replication_group_inner in ldap_connection.get_dfsr_shares():
        dfsr_shares_dict[dfsr_replication_group_name] = dfsr_replication_group_inner

    assert "Tools" in dfsr_shares_dict
    assert "tools" in dfsr_shares_dict["Tools"]["content"]
    assert 'CN=WESTDC1,OU=Domain Controllers,DC=west,DC=TestDomain,DC=test' in dfsr_shares_dict["Tools"]["servers"]


def test_get_extended_devices(ldap_connection: LdapConnection):
    keys = ['devices', 'printers', 'dns_records', 'dfsr_shares',
            'sites', 'dhcp_servers', 'fsmo_roles', 'global_catalogs', 'exchange_servers']

    extended_keys = ldap_connection.get_extended_devices_list().keys()

    assert all([True if key in extended_keys else False for key in keys])


def test_get_exchange_servers(ldap_connection: LdapConnection):
    exchange_servers = ldap_connection.get_exchange_servers()
    exchange_servers = {es['distinguishedName']: es for es in exchange_servers}

    assert "CN=DC4,CN=Servers,CN=Exchange Administrative Group (FYDIBOHF23SPDLT),CN=Administrative Groups," \
           "CN=Axonius TestDomain,CN=Microsoft Exchange,CN=Services," \
           "CN=Configuration,DC=TestDomain,DC=test" in exchange_servers


def test_get_domains_in_forest(ldap_connection: LdapConnection):
    domains_in_forest = {d['nETBIOSName']: d for d in ldap_connection.get_domains_in_forest()}
    assert domains_in_forest['WEST']['name'] == 'WEST'
    assert domains_in_forest['RAINDOMAIN']['msDS-Behavior-Version'] == 7


def test_get_report_statistics(ldap_connection: LdapConnection):
    fs = ldap_connection.get_report_statistics()
    """
    assert fs['Groups']['Builtin'] == 29
    assert fs["Forest Summary"]['Naming Master'] == "dc1.TestDomain.test"
    assert fs["Forest Features"]['Exchange Version'] == "2016"
    """
    # print("---")
    # pretty(fs)


def pretty(d, indent=0):
    print('\t' * indent + "{")
    if "dict" not in str(type(d)).lower():
        print('\t' * (indent) + str(d))
        return
    for key, value in d.items():
        if "dict" in str(type(value)).lower():
            print('\t' * indent + str(key) + ":")
            pretty(value, indent + 1)
        elif "list" in str(type(value)).lower():
            print('\t' * indent + str(key) + ": [")
            for l in value:
                pretty(l, indent + 1)
            print('\t' * indent + "]")
        else:
            print('\t' * (indent) + str(key) + ": " + str(value))
    print('\t' * indent + "}")


def get_basic_wmi_smb_command(address=ADDRESS):
    domain, username = USERNAME.split("\\")
    return ["/usr/bin/python2", WMI_SMB_RUNNER_LOCATION, domain, username, PASSWORD, address, '//./root/cimv2']


@pytest.mark.skip("python2 is not installed on the tests machine")
def test_pm():
    commands = [
        {"type": "pm", "args": [AXPM_BINARY_LOCATION, WSUSSCN2_BINARY_LOCATION]}
    ]

    p = subprocess.Popen(get_basic_wmi_smb_command(address=PM_DEVICE_ADDRESS) + [json.dumps(commands)],
                         stdout=subprocess.PIPE)

    start = time.time()
    stdout, stderr = p.communicate()
    end = time.time()

    assert (end - start) < 60 * 20    # 20 minutes
    assert p.returncode == 0
    response = json.loads(stdout)
    assert len(response) == len(commands)

    for r in response:
        print(f"Status: {r['status']}")
        print(f"Data: {r['data']}")
        if r["status"] != "ok":
            raise ValueError(f"Error, status is not ok. response: {r}")

    # A very basic test to see that we have at least one update
    assert "[Update Start]" in response[0]["data"]


@pytest.mark.skip("python2 is not installed on the tests machine")
def test_wmi():
    commands = [
        {"type": "shell", "args": ["dir"]},
        {"type": "query", "args": ["select SID from Win32_Account"]},
        {"type": "method", "args": ["StdRegProv", "EnumKey", 2147483649, ""]},
        {"type": "execbinary", "args": [TEST_BINARY_LOCATION, "\"hello, world\""]},
        # {"type": "putfile", "args": ["c:\\a.txt", "abcdefgh"]},
        # {"type": "getfile", "args": ["c:\\a.txt"]},
        # {"type": "deletefile", "args": ["c:\\a.txt"]},
    ]

    p = subprocess.Popen(get_basic_wmi_smb_command() + [json.dumps(commands)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    start = time.time()
    stdout, stderr = p.communicate()
    end = time.time()

    assert (end - start) < 60
    assert stderr == b""
    assert p.returncode == 0
    response = json.loads(stdout)
    assert len(response) == len(commands)

    for r in response:
        if r["status"] != "ok":
            raise ValueError(f"Error, status is not ok. response: {r}")

    assert "Program Files" in response[0]["data"]
    assert {'SID': 'S-1-5-21-3246437399-2412088855-2625664447-500'} in response[1]["data"]
    assert "SOFTWARE" in response[2]["data"][0]['sNames']
    assert "hello, world" in response[3]["data"]
