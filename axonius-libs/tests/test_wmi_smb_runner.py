import json
import subprocess
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
MAX_TRIES_SHARING_VIOLATION = 5


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


@pytest.mark.skip("file pm is temporarily disabled due to time")
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


def test_getfile():
    # When we have relative paths, then it is concated to the default share we define.
    # Currently, its 'ADMIN$'. In case it changes, we have to change the relative paths across the entire
    # code.
    commands = [{"type": "getfile", "args": [r"System32\Drivers\Etc\Hosts"]}]

    p = subprocess.Popen(get_basic_wmi_smb_command(address=WMI_QUERIES_DEVICE) + [json.dumps(commands)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    stdout, stderr = p.communicate(timeout=MAX_TIME_FOR_WMI_OPERATIONS)

    assert stderr == b""
    assert p.returncode == 0
    response = json.loads(stdout)
    assert len(response) == len(commands)

    r = response[0]
    assert r["status"] == "ok", f"Error, status is not ok. response: {r['status']}"
    assert "127.0.0.1" in r["data"], f"Error, hosts file does not contain 127.0.0.1: {r['data']}"


def test_axr():
    axr_queries = [
        {'type': 'query', 'args': ['select SID,LastUseTime from Win32_UserProfile']},
        {'type': 'query', 'args': ['select SID,Caption,LocalAccount,Disabled from Win32_UserAccount']},
        {'type': 'query', 'args': ['select GroupComponent, PartComponent from Win32_GroupUser']},
        {'type': 'query', 'args': ['select Vendor, Name, Version, InstallState from Win32_Product']},
        {'type': 'shell', 'args': [
            'reg query HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\ /reg:32 /s']},
        {'type': 'shell', 'args': [
            'reg query HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\ /reg:64 /s']},
        {'type': 'shell', 'args': [
            'reg query HKLM\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\ /reg:32 /s']},
        {'type': 'shell', 'args': [
            'reg query HKLM\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\ /reg:64 /s']},
        {'type': 'shell', 'args': [
            'for /f %a in (\'reg query hku\') do (reg query "%a\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall" /reg:64 /s)']},
        {'type': 'shell', 'args': [
            'for /f %a in (\'reg query hku\') do (reg query "%a\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall" /reg:32 /s)']},
        {'type': 'query', 'args': [
            'select Name, AddressWidth, NumberOfCores, LoadPercentage, Architecture, MaxClockSpeed from Win32_Processor']},
        {'type': 'query', 'args': ['select SMBIOSBIOSVersion, SerialNumber from Win32_BIOS']},
        {'type': 'query', 'args': [
            'select Caption, Description, Version, BuildNumber, InstallDate, TotalVisibleMemorySize, FreePhysicalMemory, NumberOfProcesses, LastBootUpTime from Win32_OperatingSystem']},
        {'type': 'query', 'args': ['select Name, FileSystem, Size, FreeSpace from Win32_LogicalDisk']},
        {'type': 'query', 'args': ['select HotFixID, InstalledOn from Win32_QuickFixEngineering']},
        {'type': 'query', 'args': ['select * from Win32_ComputerSystem']},
        {'type': 'query', 'args': ['select Description, EstimatedChargeRemaining, BatteryStatus from Win32_Battery']},
        {'type': 'query', 'args': ['select Caption from Win32_TimeZone']},
        {'type': 'query', 'args': ['select SerialNumber from Win32_BaseBoard']},
        {'type': 'query', 'args': ['select IPEnabled, IPAddress, MacAddress from Win32_NetworkAdapterConfiguration']},
        {'type': 'shell', 'args': ['reg query HKLM\\SYSTEM\\CurrentControlSet\\Control\\Lsa\\ ']},
        {'type': 'query', 'args': ['select DeviceID, Name, Manufacturer from Win32_PnPEntity']},
        {'type': 'pmonline', 'args': []},
        {'type': 'shell', 'args': ["type c:\\windows\\system32\\drivers\\etc\\hosts"]}
    ]
    commands = [
        {"type": "axr", "args": [axr_queries]},
    ]

    for i in range(MAX_TRIES_SHARING_VIOLATION):  # 5 tries
        p = subprocess.Popen(get_basic_wmi_smb_command(address=AXR_DEVICE) + [json.dumps(commands)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        stdout, stderr = p.communicate(timeout=MAX_TIME_FOR_WMI_OPERATIONS)

        assert stderr == b""
        assert p.returncode == 0
        response = json.loads(stdout)

        if response[0]['status'] == 'ok':
            break  # Success
        if 'STATUS_SHARING_VIOLATION' in response[0]['data']:
            print(f"Got STATUS_SHARING_VIOLATION error. Attempt {i} out of {MAX_TRIES_SHARING_VIOLATION}")

    assert response[0]['status'] == 'ok', f'Failed after 5 times {response}'

    axr_response = response[0]['data']
    assert axr_response['status'] == 'ok'
    assert axr_response['hostname'] == 'dcny1'

    assert axr_response['data'][15]['data'][0]['DNSHostName'] == 'dcny1'
    assert "127.0.0.1" in axr_response['data'][23]['data']

    # Check pm
    titles = []
    for p in axr_response['data'][22]['data']:
        titles.append(p["Title"])

    assert "2018-05 Cumulative Update for Windows Server 2016 for x64-based Systems (KB4103720)" in titles


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
