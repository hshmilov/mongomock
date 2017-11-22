"""LdapConnection.py: Implementation of LDAP protocol connection."""

__author__ = "Ofir Yefet"

import ldap3
import exceptions


class LdapConnection:
    """Class responsible for creating an ldap connection.

    This class will use a single LDAP connection in order to retrieve
    Data from the wanted ActiveDirectory.
    """

    def __init__(self, server_addr, domain_name, user_name, user_password):
        """Class initialization.

        :param str server_addr: Server address (name of IP)
        :param str domain_name: Domain name to connect with
        :param str user_name: User name to connect with
        :param str user_password: Password
        """

        self.server_addr = server_addr
        self.domain_name = domain_name
        self.user_name = user_name
        self.user_password = user_password
        self.ldap_connection = None

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
            raise exceptions.LdapException(str(ldap_error))

    def get_device_list(self, wanted_attr=None):
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
            if wanted_attr:
                self.ldap_connection.search(
                    search_base='CN=Computers,' + self.domain_name,
                    # We chose some unique parameter
                    search_filter='(&(isCriticalSystemObject=FALSE))',
                    attributes=wanted_attr)
            else:
                self.ldap_connection.search(
                    search_base='CN=Computers,' + self.domain_name,
                    # We chose some unique parameter
                    search_filter='(&(isCriticalSystemObject=FALSE))',
                    attributes='*')
            device_list_ldap = self.ldap_connection.response
        except ldap3.core.exceptions.LDAPException as ldap_error:
            raise exceptions.LdapException(str(ldap_error))

        if len(device_list_ldap) == 0:
            return dict()

        # Getting the wanted attributes
        wanted_attr = list(device_list_ldap[0]['attributes'].keys())

        def is_wanted_attr(attr_name):
            return wanted_attr == '*' or attr_name in wanted_attr

        for one_device in device_list_ldap:
            yield {attr_name: attr_val for
                   attr_name, attr_val in one_device['attributes'].items()
                   if is_wanted_attr(attr_name)}
