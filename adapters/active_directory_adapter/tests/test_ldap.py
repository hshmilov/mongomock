# from ldap_connection import LdapConnection
import json
import subprocess
import time
import logging
import pytest
import os
from active_directory_adapter.ldap_connection import LdapConnection, SSLState
from testing.test_credentials.test_ad_credentials import ad_client1_details
from axonius.parsing_utils import ad_integer8_to_timedelta
from pprint import pprint
from datetime import timedelta

DOMAIN = ad_client1_details["domain_name"]
DOMAIN_NAME, USERNAME = ad_client1_details["user"].split("\\")
PASSWORD = ad_client1_details["password"]
ADDRESS = ad_client1_details["dc_name"]

WMI_SMB_RUNNER_LOCATION = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "wmi_smb_runner", "wmi_smb_runner.py"))


@pytest.fixture(scope="module")
def ldap_connection():
    return LdapConnection(logging.getLogger("default"), 900, ADDRESS, DOMAIN, f"{DOMAIN_NAME}\\{USERNAME}",
                          PASSWORD, None, SSLState[SSLState.Unencrypted.name], bytes([]), bytes([]),
                          bytes([]))


def test_users(ldap_connection: LdapConnection):
    users = list(ldap_connection.get_users_list())

    users_dict = {}
    for user in users:
        users_dict[user["sAMAccountName"]] = user

    assert len(users_dict) > 0
    assert users_dict['ofri']['cn'] == 'Ofri Shur'
    assert users_dict['Administrator']['adminCount'] == 1
    assert "maxPwdAge" in users_dict['ofri']['axonius_extended']


def test_devices(ldap_connection: LdapConnection):
    devices = ldap_connection.get_device_list()
    devices_dict = {}
    for device in devices:
        devices_dict[device['distinguishedName']] = device

    assert len(devices_dict) > 0

    test_device = devices_dict["CN=DESKTOP-MPP10U1,CN=Computers,DC=TestDomain,DC=test"]
    assert test_device["name"] == "DESKTOP-MPP10U1"
    assert test_device["operatingSystem"] == "Windows 10 Pro"


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
        assert r["status"] == "ok"

    assert "Program Files" in response[0]["data"]
    assert {'SID': 'S-1-5-21-4050441107-50035988-2732102988-500'} in response[1]["data"]
    assert "SOFTWARE" in response[2]["data"][0]['sNames']
