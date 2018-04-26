# from ldap_connection import LdapConnection
import json
import subprocess
import time
import pytest
import os
from active_directory_adapter.ldap_connection import LdapConnection, SSLState
from testing.test_credentials.test_ad_credentials import ad_client1_details
from axonius.utils.parsing import ad_integer8_to_timedelta
from datetime import timedelta

DOMAIN = ad_client1_details["domain_name"]
DOMAIN_NAME, USERNAME = ad_client1_details["user"].split("\\")
PASSWORD = ad_client1_details["password"]
ADDRESS = ad_client1_details["dc_name"]

ACCOUNTDISABLE = 0x0002

WMI_SMB_RUNNER_LOCATION = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "wmi_smb_runner", "wmi_smb_runner.py"))

TEST_BINARY_LOCATION = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "tests", "test_binary", "test_binary.exe"))


@pytest.fixture(scope="module")
def ldap_connection():
    return LdapConnection(900, ADDRESS, DOMAIN, f"{DOMAIN_NAME}\\{USERNAME}",
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


def test_printers(ldap_connection: LdapConnection):
    printers = ldap_connection.get_printers_list()
    printers_dict = {}
    for printer in printers:
        printers_dict[printer['distinguishedName']] = printer

    assert len(printers_dict) > 0

    test_printer = printers_dict["CN=DESKTOP-MPP10U1-AXONIUS-OFFICE-PRINTER (HP Color LaserJet MF,CN=DESKTOP-MPP10U1,"
                                 "CN=Computers,DC=TestDomain,DC=test"]
    assert test_printer["serverName"] == "DESKTOP-MPP10U1.TestDomain.test"


def test_get_domain_properties(ldap_connection: LdapConnection):
    domain_properties = ldap_connection.domain_properties
    assert "maxPwdAge" in domain_properties
    assert domain_properties['name'] == 'TestDomain'
    assert ad_integer8_to_timedelta(domain_properties["maxPwdAge"]) == timedelta(days=42)


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

    p = subprocess.Popen(
        ["/usr/bin/python2", WMI_SMB_RUNNER_LOCATION, DOMAIN, USERNAME, PASSWORD, ADDRESS,
         json.dumps(commands)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    start = time.time()
    stdout, stderr = p.communicate()
    end = time.time()

    assert (end - start) < 60
    assert stderr == b""
    response = json.loads(stdout)
    assert len(response) == len(commands)

    for r in response:
        if r["status"] != "ok":
            raise ValueError(f"Error, status is not ok. response: {r}")

    assert "Program Files" in response[0]["data"]
    assert {'SID': 'S-1-5-21-3246437399-2412088855-2625664447-500'} in response[1]["data"]
    assert "SOFTWARE" in response[2]["data"][0]['sNames']
    assert "hello, world" in response[3]["data"]
