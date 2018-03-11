"""LdapConnection.py: Implementation of LDAP protocol connection."""
import ssl
from enum import Enum, auto

import ldap3

from active_directory_adapter.exceptions import LdapException
from retrying import retry

from axonius.utils.files import create_temp_file


class SSLState(Enum):
    Unencrypted = auto()
    Verified = auto()
    Unverified = auto()


class LdapConnection:
    """Class responsible for creating an ldap connection.

    This class will use a single LDAP connection in order to retrieve
    Data from the wanted ActiveDirectory.
    """

    def __init__(self, logger, ldap_page_size, server_addr, domain_name,
                 user_name, user_password, dns_server,
                 use_ssl: SSLState=SSLState.Unverified, ca_file_data: bytes=None, cert_file: bytes=None,
                 private_key: bytes = None):
        """Class initialization.

        :param obj logger: Logger object to send logs
        :param int ldap_page_size: Amount of devices to fetch on each request
        :param str server_addr: Server address (name of IP)
        :param str domain_name: Domain name to connect with
        :param str user_name: User name to connect with
        :param str user_password: Password
        :param str dns_server: Address of other dns server
        :param bool use_ssl: Whether or not to use ssl. If true, ca_file_data, cert_file and private_key must be set
        """

        self.server_addr = server_addr
        self.domain_name = domain_name
        self.user_name = user_name
        self.user_password = user_password
        self.dns_server = dns_server
        self.ldap_connection = None
        self.ldap_page_size = ldap_page_size
        self.__use_ssl = use_ssl

        if self.__use_ssl != SSLState.Unencrypted:
            self.__ca_file = create_temp_file(ca_file_data) if ca_file_data else None
            self.__cert_file = create_temp_file(cert_file) if cert_file else None
            self.__private_key_file = create_temp_file(private_key) if private_key else None

        self.logger = logger
        self._connect_to_server()

    def _connect_to_server(self):
        """This function will connect to the LDAP server.

        :raises exceptions.LdapException: In case of error in the LDAP protocol
        """
        try:
            if self.__use_ssl != SSLState.Unencrypted:
                validation = ssl.CERT_REQUIRED if self.__use_ssl == SSLState.Verified else ssl.CERT_NONE
                tls = ldap3.Tls(
                    local_private_key_file=self.__private_key_file.name if self.__private_key_file else None,
                    local_certificate_file=self.__cert_file.name if self.__cert_file else None,
                    ca_certs_file=self.__ca_file.name if self.__ca_file else None,
                    validate=validation)
                ldap_server = ldap3.Server(self.server_addr, connect_timeout=10, use_ssl=True, tls=tls)
            else:
                ldap_server = ldap3.Server(self.server_addr, connect_timeout=10)
            self.ldap_connection = ldap3.Connection(
                ldap_server, user=self.user_name, password=self.user_password,
                raise_exceptions=True, receive_timeout=10)
            self.ldap_connection.bind()
        except ldap3.core.exceptions.LDAPException as ldap_error:
            raise LdapException(str(ldap_error))

    @retry(stop_max_attempt_number=3, wait_fixed=1000 * 3)
    def get_device_list(self):
        """Fetch device list from the ActiveDirectory.

        This function will use an LDAP query in order to get all the object under the 'COMPUTERS' tree.
        In order to distinguish between a real device and the class object, we are searching on a specific
        Object that exists only on real devices objects.

        :returns: A list with all the devices registered to this DC

        :raises exceptions.LdapException: In case of error in the LDAP protocol
        """
        try:
            # Try reconnecting. Usually, when we don't use the connection a lot, it gets disconnected.
            self._connect_to_server()

            # The search filter will get only enabled "computer" objects.
            # We are using paged search, as documented here:
            # http://ldap3.readthedocs.io/searches.html#simple-paged-search
            # The filter is an ldap filter that will filter only computer objects that are enabled. Can be found here:
            # https://www.experts-exchange.com/questions/26393164/LDAP-Filter-Active-Directory-Query-for-Enabled-Computers.html
            entry_generator = self.ldap_connection.extend.standard.paged_search(
                search_base=self.domain_name,
                search_filter='(&(objectClass=Computer)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))',
                attributes='*',
                paged_size=self.ldap_page_size,
                generator=True)

            one_device = None
            devices_count = 1
            for one_device in entry_generator:
                if one_device['type'] != 'searchResEntry':
                    # searchResEntry is not a wanted object
                    continue
                device_dict = dict(one_device['attributes'])
                if 'userCertificate' in device_dict:
                    # Special case where we want to remove 'userCertificate' key (Special case for Amdocs)
                    del device_dict['userCertificate']
                device_dict['AXON_DNS_ADDR'] = self.dns_server if self.dns_server else self.server_addr
                device_dict['AXON_DC_ADDR'] = self.server_addr
                device_dict['AXON_DOMAIN_NAME'] = self.domain_name
                devices_count += 1
                if devices_count % 1000 == 0:
                    self.logger.info(f"Got {devices_count} devices so far")
                yield device_dict

            if one_device is None:
                return []

        except ldap3.core.exceptions.LDAPException as ldap_error:
            # A specific connection is usually terminated if we do not use it a lot.
            raise LdapException(str(ldap_error))

    @retry(stop_max_attempt_number=3, wait_fixed=1000 * 3)
    def get_users_list(self):
        """
        returns a list of objects representing the users in this DC.
        an object looks like {"sid": "S-1-5...", "caption": "username@domain.name"}

        :returns: a list of objects representing the users in this DC.
        :raises exceptions.LdapException: In case of error in the LDAP protocol
        """

        try:
            # Try reconnecting. Usually, when we don't use the connection a lot, it gets disconnected.
            self._connect_to_server()

            # A paged search, to get only users of type person and class user. notice we also only get
            # the attributes we need, to make the query as lightweight as possible.
            # The user account control queries only for active users.
            # taken from https://social.technet.microsoft.com/Forums/windowsserver/
            # en-US/44048e98-b191-4d18-9839-d79ffad86f76/ldap-query-for-all-active-users?forum=winserverDS
            entry_generator = self.ldap_connection.extend.standard.paged_search(
                search_base=self.domain_name,
                search_filter='(&(objectCategory=person)(objectClass=user)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))',
                attributes=['sAMAccountName', 'objectSid'],
                paged_size=self.ldap_page_size,
                generator=True)

            for i in entry_generator:
                try:
                    # fqdn is in the format of username@domain.domainsuffix.domainsuffix... etc.
                    # so we assemble it. I'm going to assume self.domain_name does not consist "," in the domain itself,
                    # as it is not a valid url. (it looks like DC=TestDomain,DC=test)
                    # we do x[3:] to get rid of "DC=".

                    fqdn = "{0}@{1}".format(i["attributes"]["sAMAccountName"],
                                            ".".join([x[3:] for x in self.domain_name.strip().split(",")]))

                    yield {"sid": i["attributes"]["objectSid"], "caption": f"{fqdn}"}
                except KeyError:
                    pass

        except ldap3.core.exceptions.LDAPException as ldap_error:
            raise LdapException(str(ldap_error))
