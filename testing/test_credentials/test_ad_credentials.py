from test_helpers.machines import FAKE_DNS_IP
import os

fakednsaddr = FAKE_DNS_IP

ad_client1_details = {
    "password": "Password2",
    "user": "TestDomain\\Administrator",
    "dc_name": "TestDomain.test",
    "domain_name": "DC=TestDomain,DC=test",
    "dns_server_address": fakednsaddr,
    "use_ssl": "Unencrypted"
}

ad_client2_details = {
    "password": "&P?HBx-e3s",
    "user": "TestSecDomain\\Administrator",
    "dc_name": "TestSecDomain.test",
    "domain_name": "DC=TestSecDomain,DC=test",
    "dns_server_address": fakednsaddr,
}

# These devices has been configured to never sleep, so that we could try to execute code through them.
DEVICE_ID_FOR_CLIENT_1 = 'CN=DESKTOP-MPP10U1,CN=Computers,DC=TestDomain,DC=test'
DEVICE_ID_FOR_CLIENT_2 = 'CN=DESKTOP-GO8PIUL,CN=Computers,DC=TestSecDomain,DC=test'
USER_ID_FOR_CLIENT_1 = "Administrator"
USER_SID_FOR_CLIENT_1 = "S-1-5-21-3246437399-2412088855-2625664447-500"

PRINTER_NAME_FOR_CLIENT1 = "AXONIUS-OFFICE-PRINTER (HP Color LaserJet MFP M277dw)"

TEST_BINARY_LOCATION = "/home/axonius/uploaded_files/test_binary.exe"
