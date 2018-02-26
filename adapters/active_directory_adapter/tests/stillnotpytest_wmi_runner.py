# from ldap_connection import LdapConnection
import sys
import json
import subprocess
import time
from testing.test_credentials.test_ad_credentials import ad_client1_details


ad_client1_details = {
    "password": "Password1",
    "user": "TestDomain\\Administrator",
    "dc_name": "10.0.229.30",
    "domain_name": "DC=TestDomain,DC=test",
    "dns_server_address": fakednsaddr
}

DOMAIN = ad_client1_details["domain_name"]
DOMAIN_NAME, USERNAME = ad_client1_details["user"].split("\\")
PASSWORD = ad_client1_details["password"]
ADDRESS = ad_client1_details["dc_name"]

"""
def test_users(l: LdapConnection) -> bool:
    users = l.get_users_list()
    for user in users:
        print(user)
    return True
"""


def main():
    # l = LdapConnection(logging.getLogger("default"), 900, ADDRESS, DOMAIN, f"{DOMAIN_NAME}\\{USERNAME}", PASSWORD, None)
    # test_users(l)

    commands = json.dumps([
        {"type": "query", "args": ["select SID from Win32_Account"]},
        {"type": "method", "args": ["StdRegProv", "EnumKey", 2147483649, ""]},
    ])

    p = subprocess.Popen(["python", "./wmirunner/wmi_runner.py", DOMAIN, USERNAME, PASSWORD, ADDRESS, commands],
                         )

    start = time.time()
    stdout, stderr = p.communicate()
    end = time.time()

    print(f"Stdout: {stdout}\nStderr: {stderr}")
    print(f"Finished after {end-start} seconds")

    return 0


if __name__ == '__main__':
    sys.exit(main())
