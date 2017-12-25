"""LdapConnection.py: Implementation of LDAP protocol connection."""

__author__ = "Ofir Yefet"

import ldap3
from ad_exceptions import LdapException


class LdapConnection:
    """Class responsible for creating an ldap connection.

    This class will use a single LDAP connection in order to retrieve
    Data from the wanted ActiveDirectory.
    """

    def __init__(self, ldap_page_size, server_addr, domain_name, user_name, user_password, dns_server):
        """Class initialization.

        :param int ldap_page_size: Amount of devices to fetch on each request
        :param str server_addr: Server address (name of IP)
        :param str domain_name: Domain name to connect with
        :param str user_name: User name to connect with
        :param str user_password: Password
        :param str dns_server: Address of other dns server
        """

        self.server_addr = server_addr
        self.domain_name = domain_name
        self.user_name = user_name
        self.user_password = user_password
        self.dns_server = dns_server
        self.ldap_connection = None
        self.ldap_page_size = ldap_page_size

        self._connect_to_server()

    def _connect_to_server(self):
        """This function will connect to the LDAP server.

        :raises exceptions.LdapException: In case of error in the LDAP protocol
        """
        try:
            ldap_server = ldap3.Server(self.server_addr, connect_timeout=10)
            self.ldap_connection = ldap3.Connection(
                ldap_server, user=self.user_name, password=self.user_password,
                raise_exceptions=True, receive_timeout=10)
            self.ldap_connection.bind()
        except ldap3.core.exceptions.LDAPException as ldap_error:
            raise LdapException(str(ldap_error))

    def get_device_list(self):
        """Fetch device list from the ActiveDirectory.

        This function will use an LDAP query in order to get all the object under the 'COMPUTERS' tree.
        In order to distinguish between a real device and the class object, we are searching on a specific
        Object that exists only on real devices objects.

        :param wanted_attr: A list containing all the wanted attributes from the Device object. 
                            If not given, all available attributes will be returned.

        :type wanted_attr: list of str

        :returns: A list with all the devices registered to this DC

        :raises exceptions.LdapException: In case of error in the LDAP protocol
        """
        try:
            # The search filter will get only enabled "computer" objects
            entry_generator = self.ldap_connection.extend.standard.paged_search(
                search_base=self.domain_name,
                search_filter='(&(objectClass=Computer)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))',
                attributes='*',
                paged_size=self.ldap_page_size,
                generator=True)

            one_device = None

            for one_device in entry_generator:
                if one_device['type'] != 'searchResEntry':
                    continue
                device_dict = dict(one_device['attributes'])
                device_dict['AXON_DNS_ADDR'] = self.dns_server if self.dns_server else self.server_addr
                device_dict['AXON_DC_ADDR'] = self.server_addr
                device_dict['AXON_DOMAIN_NAME'] = self.domain_name
                yield device_dict

            if one_device is None:
                return []

        except ldap3.core.exceptions.LDAPException as ldap_error:
            raise LdapException(str(ldap_error))
