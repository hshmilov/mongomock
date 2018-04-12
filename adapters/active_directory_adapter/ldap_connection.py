"""LdapConnection.py: Implementation of LDAP protocol connection."""
import logging

logger = logging.getLogger(f"axonius.{__name__}")
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


LDAP_ACCOUNTDISABLE = 0x2
LDAP_DONT_EXPIRE_PASSWORD = 0x10000
LDAP_PASSWORD_NOT_REQUIRED = 0x0020


class LdapConnection(object):
    """Class responsible for creating an ldap connection.

    This class will use a single LDAP connection in order to retrieve
    Data from the wanted ActiveDirectory.
    """

    def __init__(self, ldap_page_size, server_addr, domain_name,
                 user_name, user_password, dns_server,
                 use_ssl: SSLState = SSLState.Unverified, ca_file_data: bytes = None, cert_file: bytes = None,
                 private_key: bytes = None):
        """Class initialization.

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

            # Get the domain properties (usually contains its policy)
            self.domain_properties = self.__get_domain_properties()
        except ldap3.core.exceptions.LDAPException as ldap_error:
            raise LdapException(str(ldap_error))

    def __get_domain_properties(self):
        """
        Queries for the specific domain properties. We use this to get domain-based policy variables
        like the maximum time for password until it expires.
        :return: a dict of attributes
        """
        # we do not try / except here, this function should only be called from _connect_to_server.
        # To understand how paged search works, look at get_device_list.
        entry_generator = self.ldap_connection.extend.standard.paged_search(
            search_base=self.domain_name,
            search_filter='(objectClass=domainDNS)',  # "domainDNS" and not "domain" (corresponds to "DC="..)
            attributes=['distinguishedName', 'maxPwdAge', 'name'],
            paged_size=self.ldap_page_size,
            generator=True)

        for domain in entry_generator:
            if 'attributes' in domain:
                # There should be only 1 domain in our search. But if, for some reason, we have a couple,
                # lets return the specific one. (it would be only one, there's no point in yielding)
                if domain['attributes']['distinguishedName'].lower() == self.domain_name.lower():
                    return dict(domain['attributes'])

        raise ValueError(f"Error - couldn't find domain (objectClass=domainDNS) in client {self.domain_name}!")

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
            devices_count = 0
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
                    logger.info(f"Got {devices_count} devices so far")
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
                attributes='*',
                paged_size=self.ldap_page_size,
                generator=True)

            users_count = 0
            for user in entry_generator:
                if 'attributes' in user:
                    user['attributes']['axonius_extended'] = {"maxPwdAge": self.domain_properties['maxPwdAge']}

                    users_count = users_count + 1
                    if users_count % 100 == 0:
                        logger.info(f"Got {users_count} users so far")

                    yield dict(user['attributes'])

        except ldap3.core.exceptions.LDAPException as ldap_error:
            raise LdapException(str(ldap_error))

    def change_user_enabled_state(self, distinguished_name: str, enabled: bool) -> bool:
        """
        Enable or disable an AD user
        :param distinguished_name: The distinguished name of the AD user
        :param enabled: True to leave the user "enabled" and False to disable the user
        :return:
        """
        try:
            # Try reconnecting. Usually, when we don't use the connection a lot, it gets disconnected.
            self._connect_to_server()

            self.ldap_connection.search(distinguished_name,
                                        '(objectClass=*)',
                                        ldap3.BASE,
                                        attributes=['userAccountControl'],
                                        paged_size=1)
            user_account_control = self.ldap_connection.response[0]['attributes']['userAccountControl']
            if enabled:
                new_user_account_control = user_account_control & (~LDAP_ACCOUNTDISABLE)
            else:
                new_user_account_control = user_account_control | LDAP_ACCOUNTDISABLE
            logger.info(
                f"Changing user {distinguished_name} state from {user_account_control} to {new_user_account_control}")

            if not self.ldap_connection.modify(distinguished_name,
                                               {'userAccountControl': [
                                                   (ldap3.MODIFY_REPLACE, [new_user_account_control])]}):
                logger.error(f"Failed modifying userAccountControl for {distinguished_name}")
                return False

            return True

        except ldap3.core.exceptions.LDAPException as ldap_error:
            raise LdapException(str(ldap_error))

    def change_device_enabled_state(self, distinguished_name: str, enabled: bool) -> bool:
        """
        Enable or disable an AD device
        :param distinguished_name: The distinguished name of the AD device
        :param enabled: True to leave the device "enabled" and False to disable the device
        :return:
        """
        try:
            # Try reconnecting. Usually, when we don't use the connection a lot, it gets disconnected.
            self._connect_to_server()

            self.ldap_connection.search(distinguished_name,
                                        '(objectClass=*)',
                                        ldap3.BASE,
                                        attributes=['userAccountControl'],
                                        paged_size=1)
            user_account_control = self.ldap_connection.response[0]['attributes']['userAccountControl']
            if enabled:
                new_user_account_control = user_account_control & (~LDAP_ACCOUNTDISABLE)
            else:
                new_user_account_control = user_account_control | LDAP_ACCOUNTDISABLE
            logger.info(
                f"Changing device {distinguished_name} state from {user_account_control} to {new_user_account_control}")

            if not self.ldap_connection.modify(distinguished_name,
                                               {'userAccountControl': [
                                                   (ldap3.MODIFY_REPLACE, [new_user_account_control])]}):
                logger.error(f"Failed modifying userAccountControl for {distinguished_name}")
                return False

            return True

        except ldap3.core.exceptions.LDAPException as ldap_error:
            raise LdapException(str(ldap_error))
