#!/usr/bin/env python3
"""
to make this work
pip3 install username_generator, pypng, numpy
"""
import ldap3
import sys
import random
import string
import username_generator
import png
import numpy
from io import BytesIO
from testing.test_credentials.test_ad_credentials import ad_client2_details

LDAP_DN = ad_client2_details["domain_name"]
DOMAIN_NAME, USERNAME = ad_client2_details["user"].split("\\")
PASSWORD = ad_client2_details["password"]
ADDRESS = ad_client2_details["dc_name"]

USE_SSL = False
DNS_SUFFIX = "TestSecDomain.test"
USERS_ORGANIZATIONAL_UNIT = "OU=TestOrgUsers"  # root level ou in TestSecDomain.test
COMPUTERS_ORGANIZATIONAL_UNIT = "OU=TestOrgComputers"  # root level ou in TestSecDomain.test


def get_rand_png():
    # Make an image in a numpy array for this demonstration.
    nrows = 100
    ncols = 100
    numpy.random.seed(123456)
    x = numpy.random.randn(nrows, ncols, 3)
    # Convert x to 16 bit unsigned integers.
    z = (65535 * ((x - x.min()) / x.ptp())).astype(numpy.uint16)

    # Use pypng to write z as a color PNG.
    image = BytesIO()
    writer = png.Writer(width=z.shape[1], height=z.shape[0], bitdepth=16)
    # Convert z to the Python list of lists expected by
    # the png writer.
    z2list = z.reshape(-1, z.shape[1] * z.shape[2]).tolist()
    writer.write(image, z2list)
    return image.getvalue()


class AdPopulator(object):
    """
    Populates Devices, Users and more into AD.
    """

    def __init__(self, address, domain_name, username, password, dn, dns_suffix):
        """
        :param address: The address of AD
        :param domain_name: the domain, e.g. "TestSecDomain"
        :param username:  the username, eg. "Administrator"
        :param password: The password
        :param dn: The dn, e.g. "DC=TestSecDomain ,DC=test"
        :param dns_suffix: dns suffix, like "testsecdomain.test"
        """

        self.dn = dn
        self.dns_suffix = dns_suffix
        self.ldap_server = ldap3.Server(address, connect_timeout=10, use_ssl=USE_SSL)
        self.ldap_connection = ldap3.Connection(self.ldap_server, user=f"{domain_name}\\{username}", password=password,
                                                raise_exceptions=True, receive_timeout=10)
        self.ldap_connection.bind()

    def insert_to_ad(self, dn, attributes):
        """
        Inserts an entity to AD.
        :param dn: the new dn. e.g. CN=username, CN=Users
        :param attributes: a json with ldap attributes
        :return: result on success, False on duplicate
        :raise: exception in any other problem
        """

        try:
            return self.ldap_connection.add(f"{dn}, {self.dn}", attributes=attributes)
        except ldap3.core.exceptions.LDAPEntryAlreadyExistsResult:
            return False

    def insert_random_users(self, number_of_users, optional_extra_address=None):
        for i in range(number_of_users):
            username = f'{username_generator.get_uname(10, 10, False)}-{i}'
            user_cn = f"CN={username}"
            if optional_extra_address is not None:
                user_cn = f"{user_cn}, {optional_extra_address}"

            user_attributes = {
                "objectClass": ["top", "person", "organizationalPerson", "user"],
                "objectCategory": [f"CN=Person, CN=Schema, CN=Configuration, {self.dn}"],
                "sAMAccountName": username,
                "userPrincipalName": f"{username}@{self.dns_suffix}",
                "displayName": username,
                "name": username,
                "description": "User {0} is so {1}".format(username, random.choice(["happy", "sad", "pretty", "ugly"])),
                "mail": "{0}@{1}".format(username.lower(), random.choice(["gmail.com", "yahoo.com", "axonius.com"])),
                "company": "Axonius",
                "givenName": username[:5],
                "sn": username[5:],
                "streetAddress": random.choice(["Alenbi ", "Harley ", "Orchard Road ", "Broadway ", "Via Dolorosa ",
                                                "Abbey Road "]) + str(random.getrandbits(10))
            }

            full_dn = f"{user_cn}, {self.dn}"

            print(user_cn, user_attributes)

            rv = self.insert_to_ad(user_cn, user_attributes)
            if rv is False:
                print(f"username {user_cn} already exists")

            # This is just a bonus, its not needed. But remember to add USE_SSL=True if you want it.
            # self.ldap_connection.extend.microsoft.unlock_account(user=full_dn)
            # self.ldap_connection.extend.microsoft.modify_password(user=full_dn,
            #                                                       new_password="Password2",
            #                                                       old_password=None)
            # changeUACattribute = {"userAccountControl": (ldap3.MODIFY_REPLACE, [0x200])}
            # self.ldap_connection.modify(full_dn, changes=changeUACattribute)

            self.ldap_connection.modify(f"{user_cn},{self.dn}", {'photo': (ldap3.MODIFY_REPLACE, get_rand_png())})

            if i % 100 == 0:
                print(f"Inserted {i+1} users")

    def insert_random_computers(self, number_of_computers, optional_extra_address=None):
        for i in range(number_of_computers):
            computer_name = "DESKTOP-{0}".format("".join(random.choices(string.ascii_uppercase + string.digits, k=8)))
            computer_cn = f"CN={computer_name}"
            if optional_extra_address is not None:
                computer_cn = f"{computer_cn}, {optional_extra_address}"

            computer_attributes = {
                "objectClass": ["top", "person", "organizationalPerson", "user", "computer"],
                "objectCategory": [f"CN=Computer, CN=Schema, CN=Configuration, {self.dn}"],
                "operatingSystem": random.choice(["Windows 10 Pro", "Windows 7", "Windows XP", "Windows Server 2016"]),
                "userAccountControl": 0x1000,
                "dNSHostName": f"{computer_name}.{self.dns_suffix}",
                "sAMAccountName": computer_name,
                "location": random.choice(["Tel Aviv", "New York", "Farnkfurt", "Moscow", "Beirut", "London"]),
                "name": computer_name,
                "description": f"Description of computer {computer_name}",
            }

            if random.getrandbits(1) == 1:
                computer_attributes["managedBy"] = f"CN=Administrator, CN=Users, {self.dn}"

            if random.getrandbits(1) == 1:
                computer_attributes["msNPAllowDialin"] = True

            rv = self.insert_to_ad(computer_cn, computer_attributes)
            if rv is False:
                print(f"computer {computer_cn} already exists")

            if i % 100 == 0:
                print(f"Inserted {i+1} computers so far")


def main():
    print("Initializing ADPopulator...")
    ad_populator = AdPopulator(ADDRESS, DOMAIN_NAME, USERNAME, PASSWORD, LDAP_DN, DNS_SUFFIX)

    print("Inserting computers...")
    ad_populator.insert_random_computers(1, COMPUTERS_ORGANIZATIONAL_UNIT)

    print("Inserting Users...")
    ad_populator.insert_random_users(1, USERS_ORGANIZATIONAL_UNIT)

    print("Done")
    return 0


if __name__ == '__main__':
    sys.exit(main())
