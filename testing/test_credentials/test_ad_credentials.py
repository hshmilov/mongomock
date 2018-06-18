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

# These devices has been configured to never sleep, so that we could try to execute code through them.
DEVICE_ID_FOR_CLIENT_1 = 'CN=DESKTOP-MPP10U1,CN=Computers,DC=TestDomain,DC=test'
CLIENT1_DC1_ID = 'CN=DC1,OU=Domain Controllers,DC=TestDomain,DC=test'
CLIENT1_DC4_ID = 'CN=DC4,OU=Domain Controllers,DC=TestDomain,DC=test'
DEVICE_ID_FOR_CLIENT_2 = 'CN=DESKTOP-GO8PIUL,CN=Computers,DC=TestSecDomain,DC=test'
USER_ID_FOR_CLIENT_1 = "Administrator"
USER_SID_FOR_CLIENT_1 = "S-1-5-21-3246437399-2412088855-2625664447-500"

PRINTER_NAME_FOR_CLIENT1 = "AXONIUS-OFFICE-PRINTER (HP Color LaserJet MFP M277dw)"
WMI_QUERIES_DEVICE = "dc4.testdomain.test"
PM_DEVICE_WINDOWS_SERVER_2008_NO_INTERNET_ADDRESS = "10.0.239.1"
PM_DEVICE_WINDOWS_SERVER_2012_WITH_INTERNET_ADDRESS = "10.0.2.65"
PM_DEVICE_WINDOWS_SERVER_2003_32BIT_WITH_INTERNET_ADDRESS = "10.0.2.215"

TEST_BINARY_LOCATION = "/home/axonius/uploaded_files/test_binary.exe"
