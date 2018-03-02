from test_helpers.machines import FAKE_DNS_IP


fakednsaddr = FAKE_DNS_IP

ad_client1_details = {
    "password": "Password2",
    "user": "TestDomain\\Administrator",
    "dc_name": "10.0.229.30",
    "domain_name": "DC=TestDomain,DC=test",
    "dns_server_address": fakednsaddr
}

ad_client2_details = {
    "password": "&P?HBx-e3s",
    "user": "TestSecDomain\\Administrator",
    "dc_name": "10.0.229.9",
    "domain_name": "DC=TestSecDomain,DC=test",
    "dns_server_address": fakednsaddr
}

# These devices has been configured to never sleep, so that we could try to execute code through them.
DEVICE_ID_FOR_CLIENT_1 = 'CN=DESKTOP-MPP10U1,CN=Computers,DC=TestDomain,DC=test'
DEVICE_ID_FOR_CLIENT_2 = 'CN=DESKTOP-GO8PIUL,CN=Computers,DC=TestSecDomain,DC=test'
