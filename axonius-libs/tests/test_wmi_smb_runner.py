import json
import subprocess
import time
import pytest
import os

from testing.test_credentials.test_ad_credentials import *

USERNAME = ad_client1_details["user"]
PASSWORD = ad_client1_details["password"]
ADDRESS = ad_client1_details["dc_name"]

ROOT_DIR = os.path.join(os.path.dirname(__file__), "..", "..")

WMI_SMB_RUNNER_LOCATION = os.path.abspath(
    os.path.join(ROOT_DIR, "axonius-libs", "src", "libs", "axonius-py",
                 "axonius", "utils", "wmi_smb_runner", "wmi_smb_runner.py"))

TEST_BINARY_LOCATION = os.path.abspath(
    os.path.join(ROOT_DIR, "uploaded_files", "test_binary.exe"))


# Timeout in seconds for subprocesses
MAX_TIME_FOR_PM_ONLINE_OPERATIONS = 60 * 7
MAX_TIME_FOR_WMI_OPERATIONS = 60 * 5


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


def _test_pm_online(method):
    commands = [
        {"type": "pmonline", "args": [method]}  # True for is_remote (meaning, we check RPC connection)
    ]

    p = subprocess.Popen(
        get_basic_wmi_smb_command(
            address=PM_DEVICE_WINDOWS_SERVER_2012_HEBREW_WITH_INTERNET_ADDRESS) + [json.dumps(commands)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    stdout, stderr = p.communicate(timeout=MAX_TIME_FOR_PM_ONLINE_OPERATIONS)

    assert p.returncode == 0
    response = json.loads(stdout)
    assert len(response) == len(commands)

    r = response[0]
    if r["status"] != "ok":
        raise ValueError(f"Error, status is not ok. response: {r}")

    titles = []
    for i, p in enumerate(r['data']):
        titles.append(p["Title"])
        # pretty(p)

    assert "Update for Windows Server 2012 (KB2769165)" in titles


def test_pm_online_rpc():
    _test_pm_online("rpc")


def test_pm_online_smb():
    _test_pm_online("smb")


def test_pm_online_rpc_and_fallback_smb():
    _test_pm_online("rpc_and_fallback_smb")


@pytest.mark.skip("file pm is temporairly disabled due to time")
def test_pm():
    commands = [
        {"type": "pm", "args": []}
    ]

    p = subprocess.Popen(get_basic_wmi_smb_command(address=PM_DEVICE_WINDOWS_SERVER_2008_NO_INTERNET_ADDRESS) + [json.dumps(commands)],
                         stdout=subprocess.PIPE)

    stdout, stderr = p.communicate(timeout=300)

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

    p = subprocess.Popen(get_basic_wmi_smb_command(address=WMI_QUERIES_DEVICE) + [json.dumps(commands)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    stdout, stderr = p.communicate(timeout=MAX_TIME_FOR_WMI_OPERATIONS)

    assert stderr == b""
    assert p.returncode == 0
    response = json.loads(stdout)
    assert len(response) == len(commands)

    for r in response:
        if r["status"] != "ok":
            raise ValueError(f"Error, status is not ok. response: {r}")

    assert "Program Files" in response[0]["data"]
    assert {'SID': 'S-1-5-21-3246437399-2412088855-2625664447-500'} in response[1]["data"]
    assert "Console" in response[2]["data"][0]['sNames']
    assert "hello, world" in response[3]["data"]
