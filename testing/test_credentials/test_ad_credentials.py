from test_helpers.machines import FAKE_DNS_IP

fakednsaddr = FAKE_DNS_IP

ad_client1_details = {
    "password": "Password2",
    "user": "TestDomain\\Administrator",
    "dc_name": "TestDomain.test",
    "dns_server_address": fakednsaddr,
    "use_ssl": "Unencrypted"
}

ad_client2_details = {
    "password": "&P?HBx-e3s",
    "user": "TestSecDomain\\Administrator",
    "dc_name": "TestSecDomain.test",
    "dns_server_address": fakednsaddr,
    "fetch_disabled_users": True
}

GROUPS_USERS = {
    'group': 'ESX Admins.Security Branch.TestDomain.test',
    'user': 'TestDomain\\avidor',
    'password': 'Password2'
}

# These devices has been configured to never sleep, so that we could try to execute code through them.
DEVICE_ID_FOR_CLIENT_1 = 'CN=DCNY1,OU=Domain Controllers,DC=TestDomain,DC=test'
CLIENT1_DEVICE_ID_BLACKLIST = 'CN=DC4,OU=Domain Controllers,DC=TestDomain,DC=test'
CLIENT1_DC1_ID = 'CN=DC1,OU=Domain Controllers,DC=TestDomain,DC=test'
CLIENT1_DC4_ID = 'CN=DC4,OU=Domain Controllers,DC=TestDomain,DC=test'
CLIENT1_DEVICE_WITH_VULNS = 'CN=TESTWINDOWS7,CN=Computers,DC=TestDomain,DC=test'
DEVICE_ID_FOR_CLIENT_2 = 'CN=DESKTOP-GO8PIUL,CN=Computers,DC=TestSecDomain,DC=test'
USERS_IN_CLIENT_1 = [
    ('Administrator@TestDomain.test', 'S-1-5-21-3246437399-2412088855-2625664447-500'),
    ('mishka@TestDomain.test', 'S-1-5-21-3246437399-2412088855-2625664447-1114')
]
USER_ID_FOR_CLIENT_1 = USERS_IN_CLIENT_1[0][0]

PRINTER_NAME_FOR_CLIENT1 = "AXONIUS-OFFICE-PRINTER (HP Color LaserJet MFP M277dw)"
WMI_QUERIES_DEVICE = 'dcny1.TestDomain.test'
AXR_DEVICE = WMI_QUERIES_DEVICE
NONEXISTEN_AD_DEVICE_IP = '10.0.2.65'
PM_DEVICE_WINDOWS_SERVER_2008_NO_INTERNET_ADDRESS = "10.0.239.1"
PM_DEVICE_WINDOWS_SERVER_2012_HEBREW_WITH_INTERNET_ADDRESS = "10.0.2.254"

TEST_BINARY_LOCATION = "/home/axonius/shared_readonly_files/test_binary.exe"
