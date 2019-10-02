"""LdapConnection.py: Implementation of LDAP protocol connection."""

import time
import logging

from retrying import retry

from axonius.clients.ldap.exceptions import LdapException
from axonius.clients.ldap.ldap import ldap_must_get_str, ldap_must_get, ldap_get
from axonius.clients.ldap.ldap_group_cache import get_ldap_groups
from axonius.profiling.memory import asizeof
from axonius.utils.datetime import parse_date
from axonius.utils.retrying import retry_generator

logger = logging.getLogger(f'axonius.{__name__}')
import ipaddress
import struct
import itertools
from collections import defaultdict
from axonius.utils.parsing import get_exception_string, convert_ldap_searchpath_to_domain_name, \
    ad_integer8_to_timedelta, get_member_of_list_from_memberof, get_organizational_units_from_dn
from axonius.utils.files import create_temp_file
import ssl
from typing import TextIO, List, Tuple, Optional
import ldap3
from axonius.types.ssl_state import SSLState

# Connection consts
DEFAULT_LDAP_PAGE_SIZE = 900
DEFAULT_LDAP_CONNECTION_TIMEOUT = 10
DEFAULT_LDAP_RECIEVE_TIMEOUT = 120
DEFAULT_WAIT_TIME_BETWEEN_RETRIES_IN_MS = 10 * 1000  # 10 seconds
LDAP_MAX_TRIES = 5
AD_GC_PORT = 3268
AD_GC_PORT_ENCRYPTED = 3269


def connect_to_server(
        server_address: str,
        user_name: str,
        user_password: str,
        use_ssl: SSLState,
        private_key_file: TextIO,
        cert_file: TextIO,
        ca_file: TextIO,
        ldap_connection_timeout: int,
        ldap_recieve_timeout: int,
        connect_with_gc_mode: bool
) -> ldap3.Connection:
    """
    This function will connect to an LDAP server.

    :param server_address: the ip or hostname of the AD to connect to
    :param user_name: the username to use, including domain, e.g. "SomeDomain\Administrator"
    :param user_password: the user's password
    :param use_ssl: Whether or not to use SSL, and whether checking verification is needed
    :param private_key_file: if using verified SSL, the SSL files are needed
    :param cert_file:
    :param ca_file:
    :param ldap_connection_timeout: socket connection timeout in seconds
    :param ldap_recieve_timeout: socket recieve timeout in seconds
    :param connect_with_gc_mode: should connect to this dc in Global Catalog mode
    :return: The successfully binded connection
    :raises: ldap3.core.exceptions.LDAPException
    """
    if connect_with_gc_mode:
        if use_ssl != SSLState.Unencrypted:
            port = AD_GC_PORT_ENCRYPTED
        else:
            port = AD_GC_PORT
    else:
        port = None
    logger.info(f'Connecting to server {server_address}, port is {str(port)} and ssl state is {str(use_ssl)}')
    if use_ssl != SSLState.Unencrypted:
        validation = ssl.CERT_REQUIRED if use_ssl == SSLState.Verified else ssl.CERT_NONE
        is_verified = (use_ssl == SSLState.Verified)
        tls = ldap3.Tls(
            local_private_key_file=private_key_file.name if (private_key_file and is_verified) else None,
            local_certificate_file=cert_file.name if (cert_file and is_verified) else None,
            ca_certs_file=ca_file.name if (ca_file and is_verified) else None,
            validate=validation)
        ldap_server = ldap3.Server(
            server_address, connect_timeout=ldap_connection_timeout, use_ssl=True, tls=tls, port=port
        )
    else:
        ldap_server = ldap3.Server(server_address, connect_timeout=ldap_connection_timeout, port=port)

    try:
        ldap_connection = ldap3.Connection(
            ldap_server, user=user_name, password=user_password,
            raise_exceptions=True, receive_timeout=ldap_recieve_timeout)
        ldap_connection.bind()
    except Exception:
        # Try NTLM authentication as well. Username must be in the format of domain\username
        ldap_connection = ldap3.Connection(
            ldap_server, user=user_name, password=user_password,
            raise_exceptions=True, receive_timeout=ldap_recieve_timeout, authentication=ldap3.NTLM)
        ldap_connection.bind()
    return ldap_connection


EXCHANGE_VERSIONS = {
    "Version 15.": "2016",
    "Version 14.": "2010",
    "Version 08.": "2007",
    "Version 8.": "2007",
    "Version 6.5": "2003",
    "Version 6.0": "2000"
}

FUNCTIONALITY_WINDOWS_VERSIONS = {
    0: "Windows 2000",
    1: "Windows 2003 With Mixed Domains",
    2: "Windows 2003",
    3: "Windows 2008",
    4: "Windows 2008 R2",
    5: "Windows 2012",
    6: "Windows 2012 R2",
    7: "Windows 2016"
}
LDAP_MINIMUM_PSO_DOMAIN_FUNCTIONALITY_LEVEL = 3

TRUST_ATTRIBUTES_DICT = {
    0x1: "NON_TRANSITIVE",
    0x2: "UPLEVEL_ONLY",
    0x4: "QUARANTINED_DOMAIN",
    0x8: "FOREST_TRANSITIVE",
    0x10: "CROSS_ORGANIZATION",
    0x20: "WITHIN_FOREST",
    0x40: "TREAT_AS_EXTERNAL",
    0x80: "USES_RC4_ENCRYPTION",
    0x200: "CROSS_ORGANIZATION_NO_TGT_DELEGATION",
    0x400: "PIM_TRUST"
}

SITE_LINK_OPTIONS_USE_NOTIFICATION = 0x1

NTDS_CONNECTION_TWO_WAY_SYNC = 0x2

LDAP_GROUP_GLOBAL_SCOPE = 0x2
LDAP_GROUP_DOMAIN_LOCAL_SCOPE = 0x4
LDAP_GROUP_UNIVERSAL_SCOPE = 0x8
LDAP_SECURITY_GROUP = 0x80000000

LDAP_ACCOUNTDISABLE = 0x2
LDAP_ACCOUNT_LOCKOUT = 0x10
LDAP_DONT_EXPIRE_PASSWORD = 0x10000
LDAP_PASSWORD_NOT_REQUIRED = 0x0020

DNS_TYPE_A = 0x0001  # ivp4
SIZE_OF_IPV4_ENTRY_IN_BYTES = 4
DNS_TYPE_AAAA = 0x001c  # ipv6
SIZE_OF_IPV6_ENTRY_IN_BYTES = 16

# dnsRecord binary format can be seen in the get_dns_records code. but in general,
# first two bytes are the size of the "data" object, and second two bytes are the record type.
# the data object for ipv4 is 4 bytes, and for ipv6 is 16 bytes.
# so ipv4 entries will start with \x04\x00\x01\x00 and ipv6 with \x10\x00\x1c\x00.
# decode("utf") is just to make it a string object and not bytes object
IPV4_ENTRY_PREFIX = struct.pack("<HH", SIZE_OF_IPV4_ENTRY_IN_BYTES, DNS_TYPE_A).decode("utf")
IPV6_ENTRY_PREFIX = struct.pack("<HH", SIZE_OF_IPV6_ENTRY_IN_BYTES, DNS_TYPE_AAAA).decode("utf")

# the maximum nesting level of a group (ancestors a group can have)
MAXIMUM_NESTING_LEVEL = 150


class LdapConnection(object):
    """Class responsible for creating an ldap connection.

    This class will use a single LDAP connection in order to retrieve
    Data from the wanted ActiveDirectory.
    """

    def __init__(
            self, server_addr,
            user_name, user_password, dns_server=None,
            ldap_page_size=DEFAULT_LDAP_PAGE_SIZE,
            use_ssl: SSLState = SSLState.Unencrypted,
            ca_file_data: bytes=None,
            cert_file: bytes=None,
            private_key: bytes=None,
            should_fetch_disabled_devices=False,
            should_fetch_disabled_users=False,
            ldap_connection_timeout=DEFAULT_LDAP_CONNECTION_TIMEOUT,
            ldap_recieve_timeout=DEFAULT_LDAP_RECIEVE_TIMEOUT,
            connect_with_gc_mode=False,
            ldap_ou_whitelist: Optional[list] = None,
            alternative_dns_suffix: Optional[str] = None
    ):
        """Class initialization.

        :param int ldap_page_size: Amount of devices to fetch on each request
        :param str server_addr: Server address (name of IP)
        :param str user_name: User name to connect with
        :param str user_password: Password
        :param str dns_server: Address of other dns server
        :param bool use_ssl: Whether or not to use ssl. If true, ca_file_data, cert_file and private_key must be set
        :param connect_with_gc_mode: if True, connects in Global Catalog mode.
        :param ldap_ou_whitelist: a list of OU's from which we fetch entities
        :param alternative_dns_suffix: an alternative dns suffix (instead of the default one returned by ldap)
        """
        self.server_addr = server_addr
        self.user_name = user_name
        self.user_password = user_password
        self.dns_server = dns_server
        self.ldap_connection = None
        self.__ldap_page_size = ldap_page_size
        self.__ldap_connection_timeout = ldap_connection_timeout
        self.__ldap_recieve_timeout = ldap_recieve_timeout
        self.__use_ssl = use_ssl
        self.__connect_with_gc_mode = connect_with_gc_mode
        self.should_fetch_disabled_devices = should_fetch_disabled_devices
        self.should_fetch_disabled_users = should_fetch_disabled_users
        self.ca_file_data_param = ca_file_data
        self.cert_file_param = cert_file
        self.private_key_param = private_key
        if (ca_file_data or cert_file or private_key) and not (ca_file_data and cert_file and private_key):
            ca_file_data = None
            cert_file = None
            private_key = None

        self.__ca_file = create_temp_file(ca_file_data) if ca_file_data else None
        self.__cert_file = create_temp_file(cert_file) if cert_file else None
        self.__private_key_file = create_temp_file(private_key) if private_key else None
        self.__ldap_ou_whitelist = ldap_ou_whitelist
        self.__alternative_dns_suffix = alternative_dns_suffix

        self._connect_to_server()

        self.extra_sessions = {}
        self.__ldap_groups = {}

    @property
    def is_in_gc_mode(self):
        return self.__connect_with_gc_mode is True

    def get_session(self, name):
        """
        returns a new LdapConnection. This must be used to create different sessions for different therads.
        :param: a unique name indicating the the running thread.
        :return:
        """

        if name not in self.extra_sessions:
            logger.info(f"{self.server_addr}: Created new LdapConnection for name '{name}'")
            self.extra_sessions[name] = LdapConnection(
                self.server_addr, self.user_name, self.user_password,
                self.dns_server, self.__ldap_page_size, self.__use_ssl, self.ca_file_data_param, self.cert_file_param,
                self.private_key_param, self.should_fetch_disabled_devices,
                self.should_fetch_disabled_users)

        return self.extra_sessions[name]

    def set_ldap_page_size(self, ldap_page_size: int):
        self.__ldap_page_size = ldap_page_size

    def set_ldap_connection_timeout(self, ldap_connection_timeout: int):
        self.__ldap_connection_timeout = ldap_connection_timeout

    def set_ldap_recieve_timeout(self, ldap_recieve_timeout: int):
        self.__ldap_recieve_timeout = ldap_recieve_timeout

    def reconnect(self):
        """
        Reconnect to the server.
        :return:
        """

        try:
            self.disconnect()
        except Exception:
            pass

        self._connect_to_server()

    def disconnect(self):
        """
        Disconnect from the server.
        :return:
        """

        self.ldap_connection.unbind()

    def _connect_to_server(self):
        """This function will connect to the LDAP server.

        :raises exceptions.LdapException: In case of error in the LDAP protocol
        """
        try:
            self.ldap_connection = connect_to_server(
                self.server_addr, self.user_name, self.user_password,
                self.__use_ssl, self.__private_key_file, self.__cert_file,
                self.__ca_file, self.__ldap_connection_timeout, self.__ldap_recieve_timeout, self.__connect_with_gc_mode
            )

            # Get domain configurations. The following have to be, they are critical values
            # like 'distinguishedName'.
            self.root_dse = self.get_dc_properties()
            self.domain_name = ldap_must_get_str(self.root_dse, 'defaultNamingContext')
            self.configuration_naming_context = ldap_must_get_str(self.root_dse, 'configurationNamingContext')
            self.schema_naming_context = ldap_must_get_str(self.root_dse, "schemaNamingContext")
            try:
                self.current_connected_dc = ldap_must_get_str(self.root_dse, 'dnsHostName')
            except Exception:
                logger.exception(f'Can not get the currently connected DC')
                self.current_connected_dc = ''

            # This is constant.
            self.domaindnszones_naming_context = f"DC=DomainDnsZones,{self.domain_name}"
            self.forestdnszones_naming_context = f"DC=ForestDnsZones,{self.domain_name}"

            # Get the domain properties (usually contains its policy)
            self.domain_properties = self.get_domain_properties()
            try:
                self.domain_version = ldap_get(self.domain_properties, 'msDS-Behavior-Version', int) or 0
            except Exception:
                logger.exception(f'Failed to get domain version')
                self.domain_version = 0
        except ldap3.core.exceptions.LDAPException:
            raise LdapException(get_exception_string())

    def _ldap_search(self, search_filter, attributes=None, search_base=None, search_scope=None):
        """
        Searches a paged search.
        :param search_filter: the search filter.
        :param attributes: a list of strings indicating the attributes (or None for all attributes)
        :param search_base: an optional search base which is different than the domain specified in the initialization.
        :param search_scope: an optional search scope. by default this is subtree
        :return: a generator
        :raises exceptions.LdapException: In case of error in the LDAP protocol
        """
        if attributes is None:
            attributes = '*'

        if search_base is None:
            # Note! an empty string search base is a valid search base for GC. So, do not change to 'if search_base'!
            search_base = self.domain_name

        if search_scope is None:
            search_scope = ldap3.SUBTREE

        # We are using paged search, as documented here:
        # http://ldap3.readthedocs.io/searches.html#simple-paged-search
        # The filter is an ldap filter that will filter only computer objects that are enabled. Can be found here:
        # https://www.experts-exchange.com/questions/26393164/LDAP-Filter-Active-Directory-Query-for-Enabled-Computers.html

        # Note! We must make a try except here and not a @retry of the function.
        # 1. retry doesn't support generators
        # 2. even if it did support, if we have an exception in the middle of a generator
        # we don't wanna re-start it from the beginning - in that case we have to raise an exception.

        # TODO: what if the connection ends in the middle? check that scenario.
        # TODO: Also, if too much info returns, this can cause this to make stuck. also check scenario.

        def ldap_paged_search():
            return self.ldap_connection.extend.standard.paged_search(
                search_base=search_base,
                search_filter=search_filter,
                search_scope=search_scope,
                attributes=attributes,
                paged_size=self.__ldap_page_size,
                generator=True)

        try:
            entry_generator = ldap_paged_search()
            try:
                first_result = next(entry_generator)   # test the connection
                if first_result['type'] == 'searchResEntry':
                    yield first_result['attributes']
            except StopIteration:
                # If that is empty, its fine too. The next generation iteration will simply yield nothing.
                pass
        except ldap3.core.exceptions.LDAPNoSuchObjectResult:
            # This shouldn't trigger a reconnect
            raise
        except ldap3.core.exceptions.LDAPException:
            # No need to do that a couple of times. There is a logic in the adapters themselves
            # that tries more times if that fails.
            logger.exception("ldap paged search exception, retrying to connect.")
            self.reconnect()
            entry_generator = ldap_paged_search()

        for entry in entry_generator:
            if entry['type'] == 'searchResEntry':
                yield entry['attributes']

    def _ldap_modify(self, distinguished_name, changes_dict):
        """
        Modifies a specific dn.
        :param distinguished_name: the dn
        :param changes_dict: a dict consisting of key: value to replace.
        :return: True on success
        """

        changes = {}
        for key, value in changes_dict.items():
            assert key not in changes
            changes[key] = [(ldap3.MODIFY_REPLACE, [value])]

        # Note! We must make a try except here and not a @retry of the function:
        # 1. retry doesn't support generators
        # 2. even if it did support, if we have an exception in the middle of a generator
        # we don't wanna re-start it from the beginning - in that case we have to raise an exception.

        def ldap_connection_modify():
            return self.ldap_connection.modify(distinguished_name, changes)

        try:
            result = ldap_connection_modify()
        except ldap3.core.exceptions.LDAPException:
            # Try reconnecting. Usually, when we don't use the connection a lot, it gets disconnected.
            # No need to do that a couple of times. There is a logic in the adapters themselves
            # that tries more times if that fails.
            self._connect_to_server()
            result = ldap_connection_modify()

        if result is not True:
            raise ValueError("ldap3 connection modify returned False")

        return result

    def get_dc_properties(self):
        """
        Queries for the DC's properties.
        :return: a dict with such properties.
        """

        # We need to query the base (what is called, "LDAP://rootDSE"). This contains some of the current
        # dc properties, which also give info about the whole domain.
        # Note! we bring only one record (scope=base, not level/subtree).
        dc_properties = list(self._ldap_search("(objectClass=*)", search_base='', search_scope=ldap3.BASE))[0]
        return dc_properties

    def get_domain_properties(self):
        """
        Queries for the specific domain properties. We use this to get domain-based policy variables
        like the maximum time for password until it expires.
        :return: a dict of attributes
        """

        domain_generator = self._ldap_search('(objectClass=domainDNS)')
        for domain in domain_generator:
            # There should be only 1 domain in our search. But if, for some reason, we have a couple,
            # lets return the specific one. (it would be only one, there's no point in yielding)
            if domain['distinguishedName'].lower() == self.domain_name.lower():
                return dict(domain)

        raise ValueError(f"Error - couldn't find domain (objectClass=domainDNS) in client {self.domain_name}!")

    def get_domains_in_forest(self):
        try:
            return list(self._ldap_search("(nETBiosName=*)",
                                          search_base=f"CN=Partitions,{self.configuration_naming_context}"))
        except Exception:
            logger.exception("Error while getting domains in forest")
            return []

    def get_domain_prefix_to_dns_dict(self) -> dict:
        result = {}

        # This gets the translation table for all known domains by this DC
        try:
            for dom in self.get_domains_in_forest():
                netbios_name = ldap_get(dom, 'nETBiosName', str, '')
                dns_root = ldap_get(dom, 'dnsRoot', str, '')
                if not netbios_name or not dns_root:
                    logger.error(f'Bad domain {dom}! skipping')

                result[netbios_name.lower()] = dns_root.lower()
        except Exception:
            pass

        # If that did not succeed (this might be the case with non-GC DC's) we just apply the current domain
        if not result:
            result = {}
            dns_root = convert_ldap_searchpath_to_domain_name(self.domain_name)
            netbios_name = ldap_get(self.domain_properties, 'name', str, '')
            if dns_root and netbios_name:
                result[netbios_name.lower()] = dns_root.lower()

        return result

    def get_global_catalogs(self):
        """
        returns a list of dnsHostName strings, representing the global catalogs of this forest.
        :return:
        """

        gc_list = []

        try:
            # Return all GC's. from https://msdn.microsoft.com/en-us/library/ms675564(v=vs.85).aspx:
            # This filter uses the LDAP_MATCHING_RULE_BIT_AND matching rule operator (1.2.840.113556.1.4.803) to find
            # nTDSDSAobjects that have the low-order bit set in the bitmask of the options attribute.
            # The low-order bit, which corresponds to the NTDSDSA_OPT_IS_GC constant defined in Ntdsapi.h
            global_catalogs_ntdsa = self._ldap_search("(&(objectCategory=nTDSDSA)(options:1.2.840.113556.1.4.803:=1))",
                                                      attributes=["distinguishedName"],
                                                      search_base=self.configuration_naming_context)

            for gc_ntdsa in global_catalogs_ntdsa:
                # Get their parent. the dn of nTDSDSA objects always stars with "CN=NTDS Settings,"
                # And they have to be in a very specific. always under the site's servers!
                # CN=NTDS Settings,CN=DC1,CN=Servers,CN=TestDomain-TelAviv,
                # CN=Sites,CN=Configuration,DC=TestDomain,DC=test
                dn = ldap_must_get_str(gc_ntdsa, 'distinguishedName').replace("CN=NTDS Settings,", "")

                # Now Lets query for the dnshostname of this object. This is in the config schema.
                try:
                    dns_hostname = self._ldap_search("(dnsHostName=*)",
                                                     attributes=["dnsHostName"],
                                                     search_base=dn,
                                                     search_scope=ldap3.BASE)

                    # There should always be 1 here. because its the parent of an object we already found.
                    gc_list.append(ldap_must_get_str(list(dns_hostname)[0], 'dnsHostName'))
                except Exception:
                    logger.exception(f"Couldn't find a gc hostname {dn}")
        except Exception:
            logger.exception("Exception while getting global catalogs")

        # The maximum length of this strings list is the number of dc's of this domain, so no need in yielding.
        return gc_list

    def get_fsmo_roles(self):
        """
        understand who is the pdc emulator, rid master, infra master of this domain,
        and schema master, naming master of this forest.
        :return: dict of dnshostnames for each one of these roles.
        """

        # We need to query some objects to get their "fSMORoleOwner" which points to a specific record.
        # The parent of this specific record contains the dns host name of the server with that role.
        # so this function returns such dnshostname.
        def get_dnshostname_from_ldap_generator(query_answer):
            """
            Takes an answer generator and makes another ldap search request to get the dns host name.
            :param query_answer: a generator object returned from ldap serach
            :return:
            """
            try:
                # There should be only one
                role_owner_dn = ldap_must_get_str(list(query_answer)[0], 'fSMORoleOwner')

                # This always starts with CN=NTDS Settings, we need the parent.
                # It has to be in this specific format.
                role_owner_dn = role_owner_dn.replace("CN=NTDS Settings,", "")

                # Now Lets query for the dnshostname of this object. This is in the config schema.
                try:
                    dns_hostname = self._ldap_search("(dnsHostName=*)",
                                                     attributes=["dnsHostName"],
                                                     search_base=role_owner_dn,
                                                     search_scope=ldap3.BASE)

                    return ldap_must_get_str(list(dns_hostname)[0], "dnsHostName")
                except Exception:
                    logger.exception(f"error pasring dnshostname of fsmo role {role_owner_dn}")
            except Exception:
                logger.exception("exception in get_fsmo_roles")

            return ""

        fsmo_dict = dict()
        # Domain Configurations
        fsmo_dict['pdc_emulator'] = get_dnshostname_from_ldap_generator(
            self._ldap_search("(&(objectClass=domainDNS)(fSMORoleOwner=*))", attributes=["fSMORoleOwner"])
        )

        fsmo_dict['rid_master'] = get_dnshostname_from_ldap_generator(
            self._ldap_search("(&(objectClass=rIDManager)(fSMORoleOwner=*))", attributes=["fSMORoleOwner"])
        )

        fsmo_dict['infra_master'] = get_dnshostname_from_ldap_generator(
            self._ldap_search("(&(objectClass=infrastructureUpdate)(fSMORoleOwner=*))", attributes=["fSMORoleOwner"])
        )

        # Forest Configurations
        fsmo_dict['schema_master'] = get_dnshostname_from_ldap_generator(
            self._ldap_search("(&(objectClass=dMD)(fSMORoleOwner=*))",
                              attributes=["fSMORoleOwner"],
                              search_base=self.schema_naming_context)
        )

        fsmo_dict['naming_master'] = get_dnshostname_from_ldap_generator(
            self._ldap_search("(&(objectClass=crossRefContainer)(fSMORoleOwner=*))",
                              attributes=["fSMORoleOwner"],
                              search_base=self.configuration_naming_context)
        )

        return fsmo_dict

    def get_dhcp_servers(self):
        """
        returns a list of all dhcp servers
        :return: list of dnsHostName
        """

        result_dhcp_servers_list = []
        dhcp_servers = self._ldap_search("(objectClass=dHCPClass)",
                                         attributes=["dhcpServers"],
                                         search_base=self.configuration_naming_context)
        for ds in dhcp_servers:
            try:
                dhcp_servers_list = ldap_get(ds, 'dhcpServers', list)
                if dhcp_servers_list is not None and dhcp_servers_list != "":
                    # the format is defined here https://msdn.microsoft.com/en-us/library/ee915492.aspx
                    # an example of a record: "i10.0.2.199$rcn=dc3.testdomain.test$f0x00000000$sdc3.testdomain.test$"
                    for dhcp_servers_string in dhcp_servers_list:
                        dhcp_servers_string = dhcp_servers_string.split("$")
                        for token in dhcp_servers_string:
                            if token.startswith("s"):
                                # the server starts with "s". so remove the "s" (start from [1:])
                                result_dhcp_servers_list.append(token[1:])
                                break
            except Exception:
                logger.exception(f"Error while parsing dhcp server {ds}")

        # usually there are only few so no need in yield here.
        return result_dhcp_servers_list

    def get_sites(self):
        return self._ldap_search("(objectClass=site)", search_base=self.configuration_naming_context)

    def get_subnets(self):
        return self._ldap_search("(objectClass=subnet)", search_base=self.configuration_naming_context)

    def get_dfsr_shares(self):
        # Try to get the exact location of the dfsr object. But if we don't find it, then just use a specific
        # path in which it is usually (if not always) there.
        try:
            # there should only be one objectclass like this.
            dfsr_configuration_object = list(self._ldap_search("(objectClass=msDFSR-GlobalSettings)"))
            assert len(dfsr_configuration_object) == 1
            search_base = ldap_must_get_str(dfsr_configuration_object[0], 'distinguishedName')
        except Exception:
            search_base = f"CN=DFSR-GlobalSettings,CN=System,{self.domain_name}"

        # Get the whole subtree. We then organize it the way we want.
        dfsr_shares = dict()
        try:
            dfsr_configurations_subtree = self._ldap_search(
                "(|(objectClass=msDFSR-ReplicationGroup)(objectClass=msDFSR-ContentSet)(objectClass=msDFSR-Member))",
                attributes=['objectClass',
                            'distinguishedName',
                            'cn',
                            'msDFSR-ComputerReference'],
                search_base=search_base)

            # Since we get a lot of records of the same subtree, we need to build a tree here.
            # First, organize all records by the classes we need.

            dfsr_replication_groups = []
            dfsr_content_sets = []
            dfsr_members = []

            # Organize by classes
            for dfsr_item in dfsr_configurations_subtree:
                if "msDFSR-ReplicationGroup" in ldap_must_get(dfsr_item, 'objectClass', list):
                    dfsr_replication_groups.append(dfsr_item)
                elif "msDFSR-ContentSet" in ldap_must_get(dfsr_item, 'objectClass', list):
                    dfsr_content_sets.append(dfsr_item)
                elif "msDFSR-Member" in ldap_must_get(dfsr_item, 'objectClass', list):
                    dfsr_members.append(dfsr_item)

            # build tree. dfsr shares is a dict of replication groups, with their content and servers.
            # e.g.
            # dfsr_shares = {"SHARE": {"content": ["share1", "share2"], "servers": ["dc1.testdomain.test"]}}

            for rg in dfsr_replication_groups:
                dfsr_shares[ldap_must_get_str(rg, 'cn')] = {"content": [], "servers": []}

            for content_set in dfsr_content_sets:
                # Adding that in case there are problems with the dfsr share values
                try:
                    # dn should look like "CN={content_name},CN=Content,CN={replication_group_name},..."
                    replication_group_cn = ldap_must_get_str(content_set, 'distinguishedName').split(",")[
                        2][3:].replace("\\\\", "\\")
                    dfsr_shares[replication_group_cn]['content'].append(content_set['cn'])
                except Exception:
                    logger.exception(f"Problem getting replication group for {content_set}")

            for server in dfsr_members:
                try:
                    # dn should look like "CN={member_name},CN=Topology,CN={replication_group_name},..."
                    replication_group_cn = ldap_must_get_str(server, 'distinguishedName').split(",")[
                        2][3:].replace("\\\\", "\\")
                    if "msDFSR-ComputerReference" in server:
                        dfsr_shares[replication_group_cn]['servers'].append(server['msDFSR-ComputerReference'])
                except Exception:
                    logger.exception(f"Problem getting server for {server}")

        except Exception:
            logger.exception("exception while getting dfsr shares")

        yield from dfsr_shares.items()

    def get_printers_list(self):
        """
        Returns all printers in the directory.
        :return:
        """
        printers_generator = self._ldap_search('(objectClass=printQueue)')
        printers_count = 0
        for printer in printers_generator:
            printers_count = printers_count + 1
            if printers_count % 100 == 0:
                logger.info(f"Got {printers_count} users so far")

            yield dict(printer)

    def get_password_settings_objects_by_dn(self):
        pso_dict = {}
        for pso in self._ldap_search('(objectClass=msDS-PasswordSettings)'):
            pso_dict[pso['distinguishedName']] = pso

        return pso_dict

    def __get_ldap_primary_group_name(self, pgid):
        _, pgid_to_dn = get_ldap_groups(self)

        if pgid and isinstance(pgid, list):
            pgid = pgid[0]
        if pgid:
            return pgid_to_dn.get(str(pgid))
        return None

    @retry_generator(wait_fixed=DEFAULT_WAIT_TIME_BETWEEN_RETRIES_IN_MS, stop_max_attempt_number=LDAP_MAX_TRIES)
    def get_device_list(self):
        """Fetch device list from the ActiveDirectory.

        This function will use an LDAP query in order to get all the object under the 'COMPUTERS' tree.
        In order to distinguish between a real device and the class object, we are searching on a specific
        Object that exists only on real devices objects.

        :returns: A list with all the devices registered to this DC

        :raises exceptions.LdapException: In case of error in the LDAP protocol
        """
        if self.should_fetch_disabled_devices is True:
            search_filter = '(objectClass=Computer)'
        else:
            search_filter = '(&(objectClass=Computer)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))'

        devices_generator = self._ldap_search(search_filter, attributes=['*', 'canonicalName'])

        one_device = None
        devices_count = 0
        logger.info(f'LDAP - Starting to get device list')
        for one_device in devices_generator:
            device_dict = dict(one_device)
            try:
                if self.__ldap_ou_whitelist:
                    ous = get_organizational_units_from_dn(device_dict.get('distinguishedName')) or []
                    # ou's is a list of the current ou's, __ldap_ou_whitelist is a whitelist. If we do not have
                    # intersection between them then this entity is not in the current OU's.
                    if not bool(set(ous) & set(self.__ldap_ou_whitelist)):
                        continue
            except Exception:
                logger.exception(f'problem whitelisting devices by OUs')
            if 'userCertificate' in device_dict:
                # Special case where we want to remove 'userCertificate' key (Special case for Amdocs)
                del device_dict['userCertificate']
            device_dict['AXON_DNS_ADDR'] = self.dns_server if self.dns_server else self.server_addr
            device_dict['AXON_DC_ADDR'] = self.server_addr
            device_dict['AXON_DOMAIN_NAME'] = self.domain_name
            device_dict['AXON_CURRENT_CONNECTED_DC'] = self.current_connected_dc
            if self.__alternative_dns_suffix:
                device_dict['alternative_dns_suffix'] = self.__alternative_dns_suffix
            primary_group_dn = self.__get_ldap_primary_group_name(device_dict.get('primaryGroupID'))
            if primary_group_dn:
                device_dict['primary_group_name'] = primary_group_dn
            devices_count += 1

            if devices_count % 1000 == 0:
                logger.debug(f"Got {devices_count} devices so far")  # this is also printer in pluginbase
            yield device_dict

        logger.info(f"{self.server_addr}: Finished with {devices_count} users.")
        if one_device is None:
            return

    @retry_generator(wait_fixed=DEFAULT_WAIT_TIME_BETWEEN_RETRIES_IN_MS, stop_max_attempt_number=LDAP_MAX_TRIES)
    def get_users_list(self, should_get_nested_groups_for_user=True):
        """
        returns a list of objects representing the users in this DC.
        an object looks like {"sid": "S-1-5...", "caption": "username@domain.name"}

        :returns: a list of objects representing the users in this DC.
        :raises exceptions.LdapException: In case of error in the LDAP protocol
        """

        # Note that we also bring inetOrgPerson which are person users (same schema, so same attributes etc)
        # some organizations use this (might happen on migrations of domains)

        if self.should_fetch_disabled_users is True:
            search_filter = '(&(objectCategory=person)(|(objectClass=user)(objectClass=inetOrgPerson)))'
        else:
            search_filter = '(&(objectCategory=person)(|(objectClass=user)(objectClass=inetOrgPerson))(!(userAccountControl:1.2.840.113556.1.4.803:=2)))'

        logger.info(f'LDAP - Starting to get users list')
        if self.domain_version >= LDAP_MINIMUM_PSO_DOMAIN_FUNCTIONALITY_LEVEL:
            # We have to specify it since this is calculated upon request.
            attributes = ['*', 'msDS-ResultantPSO', 'canonicalName']
            try:
                psos = self.get_password_settings_objects_by_dn()
            except Exception:
                psos = dict()
        else:
            attributes = ['*', 'canonicalName']
            psos = dict()
        users_generator = self._ldap_search(search_filter, attributes=attributes)
        users_count = 0
        get_users_start = time.time()
        for user in users_generator:
            try:
                if self.__ldap_ou_whitelist:
                    ous = get_organizational_units_from_dn(user.get('distinguishedName')) or []
                    # ou's is a list of the current ou's, __ldap_ou_whitelist is a whitelist. If we do not have
                    # intersection between them then this entity is not in the current OU's.
                    if not bool(set(ous) & set(self.__ldap_ou_whitelist)):
                        continue
            except Exception:
                logger.exception(f'Problem whitelisting users by OUs')
            try:
                if should_get_nested_groups_for_user:
                    member_of_full_for_user = \
                        list(self.get_nested_groups_for_object({'memberOf': user.get('memberOf') or []}))
                else:
                    member_of_full_for_user = None
            except Exception:
                logger.exception(f'Problem getting nested groups for object, passing and reconnecting')
                member_of_full_for_user = None

            primary_group_dn = self.__get_ldap_primary_group_name(user.get('primaryGroupID'))
            if primary_group_dn:
                user['primary_group_name'] = primary_group_dn

            if self.domain_version >= LDAP_MINIMUM_PSO_DOMAIN_FUNCTIONALITY_LEVEL:
                try:
                    user_pso_dn = ldap_get(user, 'msDS-ResultantPSO', str)
                    user_pso = psos.get(user_pso_dn)
                    # If we have a pso, get the maximum password age if it exists (if not - there is no limit)
                    # if not - the max password age is the domain's level max password age
                    if user_pso:
                        if user_pso.get('msDS-MaximumPasswordAge'):
                            maximum_password_age = ldap_get(user_pso, 'msDS-MaximumPasswordAge', int) or None
                        else:
                            maximum_password_age = None
                    else:
                        maximum_password_age = self.domain_properties.get('maxPwdAge')
                except Exception:
                    logger.exception(f'Problem parsing maximum password age')
                    maximum_password_age = None
            else:
                maximum_password_age = self.domain_properties.get('maxPwdAge')

            user['axonius_extended'] = {
                "maxPwdAge": maximum_password_age,
                'member_of_full': member_of_full_for_user
            }

            user['AXON_DNS_ADDR'] = self.dns_server if self.dns_server else self.server_addr
            user['AXON_DC_ADDR'] = self.server_addr
            user['AXON_DOMAIN_NAME'] = self.domain_name
            user['AXON_CURRENT_CONNECTED_DC'] = self.current_connected_dc

            users_count = users_count + 1
            if users_count % 1000 == 0:
                logger.info(f"Got {users_count} users so far")
                logger.info(f'Approximate size in memory so far for ldap groups: '
                            f'{asizeof(self.__ldap_groups)/(1024**2)} mb')

            yield dict(user)

        logger.info(f"{self.server_addr}: Finished with {users_count} users.")
        logger.info(f'Finished getting all users & their groups, recursively. time: {time.time()- get_users_start}')
        logger.info(f'Approximate size in memory so far for ldap groups: '
                    f'{asizeof(self.__ldap_groups)/(1024**2)} mb')

        # There is no use in saving all of the data, we want to reduce memory & we want to fetch this again in the next
        # cycle.
        self.__ldap_groups = {}

    @retry_generator(wait_fixed=DEFAULT_WAIT_TIME_BETWEEN_RETRIES_IN_MS, stop_max_attempt_number=LDAP_MAX_TRIES)
    def get_dns_records(self, name=None):
        """
        Returns dns records for this zone.
        :param name: optional. if exists, will query only for a specific hostname. note! this should be the name
                     of the record, e.g. "WINXP", not "WINXP.TestDomain.test".
        :return: yields (name, ip_addr) where name is string and ip_addr is ipv4/ipv6 object from the ipaddress module.
        """

        logger.info(f'LDAP - Starting to get dns records')
        if name is None:
            search_query = f"(&(objectClass=dnsNode)" \
                           f"(|(dnsRecord={IPV4_ENTRY_PREFIX}*)(dnsRecord={IPV6_ENTRY_PREFIX}*)))"
        else:
            search_query = f"(&(objectClass=dnsNode)(name={name})" \
                           f"(|(dnsRecord={IPV4_ENTRY_PREFIX}*)(dnsRecord={IPV6_ENTRY_PREFIX}*)))"

        # Sometimes the dns records are in domaindnszone, but sometimes they are in forestdnszone.
        # query both objects (only the base) to see what exists.
        dns_zone_name = convert_ldap_searchpath_to_domain_name(self.domain_name)
        dns_generators = []
        for zone in [self.domaindnszones_naming_context, self.forestdnszones_naming_context]:
            try:
                full_search_base = f"DC={dns_zone_name},CN=MicrosoftDNS,{zone}"
                zone_object = list(self._ldap_search("(cn=*)",
                                                     attributes=[ldap3.NO_ATTRIBUTES],
                                                     search_base=full_search_base,
                                                     search_scope=ldap3.BASE))
                # If there is no such object, this should throw an exception by now.
                # so now we can just append the generator itself.
                dns_generators.append(self._ldap_search(
                    search_query,
                    attributes=['dnsRecord', 'name'],
                    search_base=full_search_base
                ))
            except ldap3.core.exceptions.LDAPNoSuchObjectResult:
                pass

        try:
            dns_record_i = 0
            for dns_record in itertools.chain(*dns_generators):
                try:
                    # Parse binary format.
                    dns_record_binary = ldap_must_get(dns_record, 'dnsRecord', list)
                    for record_binary in dns_record_binary:
                        # the binary format is as follows:
                        # https://msdn.microsoft.com/en-us/library/ee898781.aspx
                        # since i want only "type" , which is the third and fourth byte, i'm handling the rest
                        # as padding (X).

                        dns_record_i += 1
                        if dns_record_i % 5000 == 0:
                            logger.info(f"Brought {dns_record_i} dns records already")

                        record_type = struct.unpack("<2xH19x", record_binary[:23])[0]

                        # This can be ipv4 or ipv6 object.

                        if record_type == DNS_TYPE_A or record_type == DNS_TYPE_AAAA:
                            # ip_address can get a big-endian bytes object. ip_address automatically
                            # understands if its in ipv4 or ipv6 at creates the appropriate object.
                            ip_addr = ipaddress.ip_address(record_binary[24:])
                            yield (ldap_must_get_str(dns_record, 'name'), str(ip_addr))

                except Exception:
                    logger.exception(f"Error in parsing dns record {dns_record}")

            if name is None:
                # We brought many dns records.
                logger.info(f"{self.server_addr}: Finished Yielding {dns_record_i} dns records.")

                # If we were asked to bring the whole zone but didn't bring anythign..
                if dns_record_i == 0:
                    logger.warning(f"{self.server_addr}: Didn't bring any DNS Record! "
                                   f"do we have this zone? try chainging "
                                   f"search_base to only self.domaindnszones_naming_context to search the whole dns")
        except Exception:
            logger.exception("exception while querying dns")
            return

    def get_extended_devices_list(self):
        """
        Returns a lot of information about devices.
        :return:
        """
        d = dict()
        d['devices'] = self.get_device_list()
        d['printers'] = self.get_printers_list()
        d['dfsr_shares'] = self.get_dfsr_shares()
        d['sites'] = self.get_sites()  # subnets are part of sites so no need for extended subnets config
        d['dhcp_servers'] = self.get_dhcp_servers()
        d['fsmo_roles'] = self.get_fsmo_roles()
        d['global_catalogs'] = self.get_global_catalogs()
        d['exchange_servers'] = self.get_exchange_servers()
        d['dns_records'] = self.get_dns_records()

        return d

    def get_exchange_servers(self):
        """
        Note that the installation of exchange requires changes in the schema of the forest.
        This means, that this whole code must be in a try / except block since it can raise an exception,
        rather than returning empty results, if there are no exchange servers.
        :return:
        """

        try:
            # We must list() it here, because this attribute might not be in the server. if it isn't, we must
            # trigger the exception now and not in the function that receives the generator.
            return list(self._ldap_search("(&(objectClass=msExchExchangeServer)(objectCategory=msExchExchangeServer))",
                                          search_base=self.configuration_naming_context))
        except Exception:
            # might be a not found schema. we don't wanna put an exception here.
            pass

        return []

    def set_ldap_attribute(self, distinguished_name: str, attribute_name: str, attribute_value):
        """
        Sets a specific ldap attribute
        :param distinguished_name: the distinguished name of the entity
        :param attribute_name: the attribute name
        :param attribute_value: the attribute value
        :return:
        """
        return self._ldap_modify(distinguished_name, {attribute_name: attribute_value})

    def change_entity_enabled_state(self, distinguished_name: str, enabled: bool) -> bool:
        """
        Enable or disable an AD entity
        :param distinguished_name: The distinguished name of the AD user
        :param enabled: True to leave the user "enabled" and False to disable the user
        :return:
        """
        # search_scope must be BASE here, or else if we have a device with a printer or a user with some subordinate
        # objects, the result will contain them.
        entity = list(self._ldap_search('(objectClass=*)',
                                        attributes=['userAccountControl'],
                                        search_base=distinguished_name,
                                        search_scope=ldap3.BASE))
        if len(entity) != 1:
            raise ValueError(f"searched entity with dn {distinguished_name}, expected len() ==1 but got {entity}")

        user_account_control = ldap_must_get(entity[0], 'userAccountControl', int)

        if enabled:
            new_user_account_control = user_account_control & (~LDAP_ACCOUNTDISABLE)
        else:
            new_user_account_control = user_account_control | LDAP_ACCOUNTDISABLE

        logger.info(
            f"Changing entity {distinguished_name} state from {user_account_control} to {new_user_account_control}")

        return self.set_ldap_attribute(distinguished_name, 'userAccountControl', new_user_account_control)

    def get_user(self, username: str) -> Tuple[dict, List[str]]:
        """
        Get a user from AD and all nested groups it is part of
        Note! This has to be a fast function since it uses for gui logins
        :param username: Name of user
        :return: User's attributes and list of groups it is part of
        """
        search_filter = f'(&(objectCategory=person)' \
                        f'(|(objectClass=user)(objectClass=inetOrgPerson))(cn={username}))'
        search_filter_2 = f'(&(objectCategory=person)' \
                          f'(|(objectClass=user)(objectClass=inetOrgPerson))(sAMAccountName={username}))'
        result = list(self._ldap_search(search_filter, attributes=['*']))
        result_2 = list(self._ldap_search(search_filter_2, attributes=['*']))

        # Note! we do not parse primaryGroupID here, since this can take a whole lot time (many seconds). Since
        # this method is used for ldap login via gui it should be fast.
        try:
            if result:
                groups = list(self.get_nested_groups_for_object({'memberOf': result[0].get('memberOf') or []}))
                return result[0], get_member_of_list_from_memberof(groups) or []
            if result_2:
                groups = list(self.get_nested_groups_for_object({'memberOf': result_2[0].get('memberOf') or []}))
                return result_2[0], get_member_of_list_from_memberof(groups) or []
            logger.error(f'Got no response for user {username}')
        except Exception:
            logger.exception(f"Can't fetch user of user {username}")
        return None

    def __get_nested_groups_for_group(self, group_dn: str, nesting_level=0) -> set:
        """
        Takes a group DN and gets all the groups it is a member of, recursively.
        :param group_dn: the distinguished name of the group
        :param nesting_level: an inner parameter that is used like a 'call stack' to prevent infinite call which
                              will lead to stack exhaustion.
        :return: a set of the nested groups it is a member of.
        """
        try:
            if nesting_level >= MAXIMUM_NESTING_LEVEL:
                logger.error(f'Error! nesting level reached to {nesting_level}, is there a circle? '
                             f'stopping to prevent stack exhausiton.')
                return set()

            self.__ldap_groups, _ = get_ldap_groups(self)

            group_object = self.__ldap_groups.get(group_dn)
            if not group_object:
                logger.debug(f'Error! group {group_dn} is not found in our dict, this should never happen!')
                return set()

            member_of_full = group_object.get('member_of_full')
            if member_of_full is None:      # if not member_of_full will not work here, since sometimes its just set()
                if group_object.get('search_mode') is True:
                    return set()
                group_object['search_mode'] = True
                # we need to calculate it.
                member_of = group_object.get('member_of') or []
                member_of_full = set()

                for member_of_group_dn in member_of:
                    member_of_full.add(member_of_group_dn)
                    member_of_full.update(self.__get_nested_groups_for_group(member_of_group_dn, nesting_level + 1))

                group_object['search_mode'] = False
                # Only the first level of search can guarantee it got everything
                if nesting_level == 0:
                    self.__ldap_groups[group_dn]['member_of_full'] = member_of_full

            return member_of_full
        except Exception:
            logger.exception(f'Could not get nested groups for group {group_dn}')
            return set()

    def get_nested_groups_for_object(self, ad_object):
        try:
            groups = set()
            ad_object_member_of = ad_object.get('memberOf') or []
            if isinstance(ad_object_member_of, str):
                ad_object_member_of = [ad_object_member_of]
            for mo in ad_object_member_of:
                groups.add(mo)
                groups.update(self.__get_nested_groups_for_group(mo))

            return groups
        except Exception:
            logger.error(f'Error while getting nested groups for ad object {ad_object}')
            return set()

    # Statistics
    def get_report_statistics(self):
        """
        This is a very long function, which is not so divided to smaller functions
        mainly because we aren't going to be using this too much, and i want it to get done quick for thyssenkrupp.

        It's not written well - but it's written defensive. It should be rewritten.
        TODO: Make it more robust.
        :return:
        """
        total_groups = 0
        builtin = 0
        universal_security = 0
        universal_distribution = 0
        global_security = 0
        global_distribution = 0
        domain_local_security = 0
        domain_local_distribution = 0

        # Groups
        logger.info("Statistics - Groups")
        try:
            groups = self._ldap_search("(objectClass=group)", attributes=["groupType", "distinguishedName"])
            for group in groups:
                try:
                    total_groups += 1

                    # Everything under "builtin" has "CN=Builtin" in its dn.
                    if f"CN=Builtin,{self.domain_name}" in group["distinguishedName"]:
                        builtin += 1

                    # groupType defines bits to understand the group type. For more information:
                    # https://msdn.microsoft.com/en-us/library/ms675935(v=vs.85).aspx
                    group_type = int(ldap_get(group, "groupType", int, 0))
                    # if group_type < 0:
                    #     group_type = ctypes.c_ulong(group_type).value  # convert signed to unsigned

                    if group_type & LDAP_GROUP_UNIVERSAL_SCOPE:
                        if group_type & LDAP_SECURITY_GROUP:
                            universal_security += 1
                        else:
                            universal_distribution += 1

                    if group_type & LDAP_GROUP_GLOBAL_SCOPE:
                        if group_type & LDAP_SECURITY_GROUP:
                            global_security += 1
                        else:
                            global_distribution += 1

                    if group_type & LDAP_GROUP_DOMAIN_LOCAL_SCOPE:
                        if group_type & LDAP_SECURITY_GROUP:
                            domain_local_security += 1
                        else:
                            domain_local_distribution += 1
                except Exception:
                    logger.exception(f"error parsing group {group}")
        except Exception:
            total_groups = ""
            builtin = ""
            universal_security = ""
            universal_distribution = ""
            global_security = ""
            global_distribution = ""
            domain_local_security = ""
            domain_local_distribution = ""
            logger.exception("Error parsing groups statistics")

        # naming, schema, forest name, forest functionality,
        logger.info("Statistics - FSMO")
        try:
            dc = self.get_dc_properties()
            fsmo_roles = self.get_fsmo_roles()
            naming_master = fsmo_roles.get("naming_master", "")
            schema_master = fsmo_roles.get("schema_master", "")

            # convert forest name to string
            forest_name = ldap_get(dc, 'rootDomainNamingContext', str, '')
            forest_name = convert_ldap_searchpath_to_domain_name(forest_name)

            # convert forest functionality to string
            forest_functionality = ldap_get(dc, "forestFunctionality", int, -1)
            forest_functionality = int(forest_functionality)

            forest_functionality = FUNCTIONALITY_WINDOWS_VERSIONS.get(forest_functionality, "Unknown")
        except Exception:
            naming_master = ""
            schema_master = ""
            forest_name = ""
            forest_functionality = ""
            logger.exception("Can't get basic info")

        # global catalogs, exchange servers, site count, domain in forest count
        logger.info("Statistics - Special Servers & Domains")
        try:
            global_catalogs_count = len(self.get_global_catalogs())
        except Exception:
            global_catalogs_count = ""
            logger.exception("error getting global catalogs")

        try:
            exchange_servers_count = len(list(self.get_exchange_servers()))
        except Exception:
            exchange_servers_count = ""
            logger.exception("error geting exchange servers")

        try:
            domains_in_forest_count = len(list(self.get_domains_in_forest()))
        except Exception:
            domains_in_forest_count = ""
            logger.exception("error getting domains in forest count")

        # forest recycle bin
        logger.info("Statistics - Recycle Bin & Tombstone Lifetime")
        try:
            forest_enabled_features = self._ldap_search("(cn=*)",
                                                        attributes=["msDS-EnabledFeature"],
                                                        search_base=f"CN=Partitions,{self.configuration_naming_context}",
                                                        search_scope=ldap3.BASE)
            forest_enabled_features = ldap_get(list(forest_enabled_features)[0], "msDS-EnabledFeature", list, [])
            recycle_bin_enabled = any(
                [True if "Recycle Bin" in feature else False for feature in forest_enabled_features])
        except Exception:
            recycle_bin_enabled = ""
            logger.exception("Can't get recycle bin enabled")

        # forest tombstone lifetime
        try:
            tombstone_lifetime = self._ldap_search("(cn=*)",
                                                   attributes=["tombstoneLifetime"],
                                                   search_scope=ldap3.BASE,
                                                   search_base=f"CN=Directory Service,CN=Windows NT,CN=Services,{self.configuration_naming_context}")
            tombstone_lifetime = int(ldap_get(list(tombstone_lifetime)[0], "tombstoneLifetime", int, -1))
        except Exception:
            tombstone_lifetime = ""
            logger.exception("Can't get Tombstone Lifetime.")

        # forest exchange version
        logger.info("Statistics - Forest Exchange Version")
        try:
            try:
                exchange_servers = list(self._ldap_search("(objectClass=msExchExchangeServer)",
                                                          attributes=["serialNumber"],
                                                          search_base=self.configuration_naming_context))
            except Exception:
                # We don't always have exchange servers in the organization. If exchange isn't installed
                # this will throw an exception since the schema isn't defined.
                exchange_servers = []

            exchange_version = set()

            # we are going to loop through all servers and get their version.
            for es in exchange_servers:
                es_serial_number = ldap_get(es, "serialNumber", str, "")
                for version, version_name in EXCHANGE_VERSIONS.items():
                    if version in es_serial_number:
                        exchange_version.add(version_name)
                        break

            # If there is only one version (what we expect...) then this is the final version.
            exchange_version = list(exchange_version)
            if len(exchange_version) == 1:
                exchange_version = exchange_version[0]
            else:
                exchange_version = ""
        except Exception:
            exchange_version = ""
            logger.exception("Can't get exchange server version")

        # Site Links.
        logger.info("Statistics - Site Links")
        try:
            site_links = []
            forest_site_link_count = 0
            site_cn_to_site_links = defaultdict(list)
            site_links_to_site_cns = defaultdict(list)
            site_links_object = self._ldap_search(
                "(objectClass=siteLink)",
                search_base=f"CN=Inter-Site Transports,CN=Sites,{self.configuration_naming_context}"
            )
            for site_link in site_links_object:
                forest_site_link_count += 1
                site_link_name = ldap_get(site_link, "name", str, "")
                site_link_repl_interval = str(ldap_get(site_link, "replInterval", int, ""))
                site_link_cost = str(site_link.get("cost", "0"))
                site_link_type = ldap_must_get_str(site_link, "distinguishedName").split(",")[1][3:]
                site_link_sitelist = [sl.split(",")[0][3:] for sl in ldap_get(site_link, 'siteList', list, [])]
                site_link_change_notification_enabled = (
                    ldap_get(site_link, "options", int,
                             0) & SITE_LINK_OPTIONS_USE_NOTIFICATION) > 0

                site_links.append({
                    "name": site_link_name,
                    "repl_interval": site_link_repl_interval,
                    "cost": site_link_cost,
                    "type": site_link_type,
                    "sitelist": ", ".join(site_link_sitelist),
                    "change_notification_enabled": True if site_link_change_notification_enabled is True else False
                })

                # Now provide double-mapping to make things easier in the sites
                site_links_to_site_cns[site_link_name] = site_link_sitelist
                for siten in site_link_sitelist:
                    site_cn_to_site_links[siten].append(site_link_name)
        except Exception:
            logger.exception("Exception while parsing site links")
            forest_site_link_count = ""
            site_cn_to_site_links = {}
            site_links_to_site_cns = {}
            site_links = []

        # Sites
        logger.info("Statistics - Sites")
        try:
            forest_dc_count = 0
            forest_sites_count = 0
            forest_site_subnet_count = 0
            forest_site_connections_count = 0
            forest_site_without_site_connections = 0
            forest_sites_without_site_istg = 0
            forest_site_without_subnets = 0
            forest_site_without_servers = 0
            forest_sites_summary = []
            forest_site_details = []

            # go through each site, query its subnets, dc's, and domains.
            for site in self.get_sites():
                forest_sites_count += 1
                site_cn = ldap_must_get_str(site, 'cn')
                site_name = ldap_get(site, "name", str, "")
                site_location = ldap_get(site, "location", str, "")
                site_subnets = ldap_get(site, "siteObjectBL", list, [])
                if type(site_subnets) == list:
                    # each member looks like "CN=192.168.20.0/24,CN=Subnet,CN=..."
                    try:
                        site_subnets = [subnet.split(",")[0][3:] for subnet in site_subnets]
                        forest_site_subnet_count += len(site_subnets)
                    except Exception:
                        logger.exception("error parsing site subnets")
                        site_subnets = []
                else:
                    site_subnets = []

                if len(site_subnets) == 0:
                    forest_site_without_subnets += 1

                # Now get all DC's and domains in that site
                bridgehead_servers = []
                site_dcs = []
                site_domains = set()
                site_servers_count = 0
                for server in self._ldap_search("(objectClass=server)",
                                                attributes=["cn", "isDeleted", "isRecycled",
                                                            "dNSHostName", "serverReference",
                                                            "bridgeheadTransportList"],
                                                search_base=f"CN=Servers,CN={site_cn},CN=Sites,"
                                                            f"{self.configuration_naming_context}"):
                    if server.get("isDeleted") is True or server.get("isRecycled") is True:
                        continue
                    forest_dc_count += 1
                    site_servers_count += 1

                    dc_hostname = ldap_get(server, "DNSHostName", str)
                    if dc_hostname is not None:
                        site_dcs.append(dc_hostname)

                    site_domain = ldap_get(server, "serverReference", str)
                    if site_domain is not None:
                        site_domains.add(convert_ldap_searchpath_to_domain_name(site_domain))

                    bh = ldap_get(server, "bridgeheadTransportList", list, [])
                    if bh is not None and type(bh) == list and len(bh) > 0:
                        # bh is a dn, parse it
                        try:
                            bh = ",".join([cn.split(",")[0][3:] for cn in bh])
                            bridgehead_servers.append(f"{dc_hostname} ({bh})")
                        except None:
                            logger.exception("exception parsing bridgeheader server")

                if site_servers_count == 0:
                    forest_site_without_servers += 1

                # Make the domains unique
                site_domains = list(site_domains)

                # Eventually, add this new site
                if site_name != "" or site_location != "" \
                        or len(site_domains) > 0 or len(site_dcs) > 0 or len(site_subnets) > 0:
                    forest_sites_summary.append({
                        "name": site_name,
                        "location": site_location,
                        "domains": ", ".join(site_domains),
                        "dcs": ", ".join(site_dcs),
                        "subnets": ", ".join(site_subnets)
                    })

                # Now, we have some more things we'd like to know about this site, but in a different table.
                site_istg = None
                site_settings = list(self._ldap_search(
                    "(cn=*)",
                    attributes=["interSiteTopologyGenerator"],
                    search_base=f"cn=NTDS Site Settings,{site['distinguishedName']}",
                    search_scope=ldap3.BASE))

                # Should be the only one.
                if len(site_settings) == 1:
                    istg = ldap_get(site_settings[0], "interSiteTopologyGenerator", str)
                    if istg is not None:
                        # search for its dnshostname
                        try:
                            # We need to get to its parent. so remove the parent element
                            istg = ",".join(istg.split(",")[1:])
                            site_istg = list(self._ldap_search("(cn=*)", attributes=['dnsHostName'],
                                                               search_base=istg,
                                                               search_scope=ldap3.BASE))[0].get("dnsHostName")
                        except Exception:
                            # It might not exist or be disabled.
                            pass

                if site_istg is None:
                    forest_sites_without_site_istg += 1

                # adjacent sites is the list of sites we see from all of our links
                adjacent_sites = []
                for sl in site_cn_to_site_links.get(site_name, []):
                    for sn in site_links_to_site_cns.get(sl, []):
                        if sn != site_name and sn not in adjacent_sites:
                            adjacent_sites.append(sn)

                forest_site_details.append({
                    "name": site_name,
                    "options": "",
                    "istg": site_istg if site_istg is not None else "",
                    "site_links": ", ".join(site_cn_to_site_links.get(site_name, [])),
                    "bridgehead_servers": ", ".join(bridgehead_servers),
                    "adjacent_sites": ", ".join(adjacent_sites)
                })

                # Query all connections to the site.
                site_connections = []
                site_connections_object = self._ldap_search("(objectClass=nTDSConnection)",
                                                            search_base=site['distinguishedName'])
                for site_connection in site_connections_object:
                    sc_enabled = bool(site_connection.get("enabledConnection", False))
                    sc_options = ldap_get(site_connection, "options", int, 0)
                    try:
                        sc_options_int = int(sc_options)
                        if sc_options_int & NTDS_CONNECTION_TWO_WAY_SYNC > 0:
                            sc_options = "NTDS_CONNECTION_TWO_WAY_SYNC"
                        else:
                            sc_options = ""
                    except Exception:
                        sc_options = ""

                    sc_from = ldap_get(site_connection, "fromServer", str)
                    if sc_from is not None:
                        # Its a DN. Take the second part, remove "CN=".
                        sc_from = sc_from.split(",")[1][3:]
                    sc_to = ldap_must_get_str(site_connection, 'distinguishedName').split(",")[2][3:]

                    site_connections.append({
                        "connection_enabled": sc_enabled,
                        "sc_options": sc_options,
                        "sc_from": "" if sc_from is None else sc_from,
                        "sc_to": sc_to
                    })
                    forest_site_connections_count += 1

                if len(site_connections) == 0:
                    forest_site_without_site_connections += 1

        except Exception:
            forest_sites_count = ""
            forest_site_subnet_count = ""
            forest_site_connections_count = ""
            forest_site_without_site_connections = ""
            forest_site_without_subnets = ""
            forest_site_without_servers = ""
            forest_sites_without_site_istg = ""
            forest_dc_count = ""
            forest_sites_summary = []
            forest_site_details = []
            site_connections = []
            logger.exception("Error while parsing sites & dc count")

        # Subnets
        logger.info("Statistics - Subnets")
        try:
            forest_subnets = []
            for subnet in self.get_subnets():
                subnet_name = ldap_get(subnet, "name", str, "")
                subnet_location = ldap_get(subnet, "location", str, "")

                # subnet site is a dn (CN=site-name,CN=Sites)
                site_object = ldap_get(subnet, "siteObject", str)
                if site_object is not None:
                    try:
                        subnet_site = site_object.split(",")[0][3:]
                    except Exception:
                        subnet_site = ""
                        logger.exception(f"can't get subnet site for {subnet}")

                if subnet_name != "" or subnet_site != "" or subnet_location != "":
                    forest_subnets.append({
                        "name": subnet_name,
                        "site": subnet_site,
                        "location": subnet_location
                    })
        except Exception:
            forest_subnets = []
            logger.exception("Unable to get subnets")

        # Domains
        logger.info("Statistics - Domains")
        try:
            domains_desc = []
            password_policies = []
            domains_obj = self.get_domains_in_forest()

            for dom in domains_obj:
                dom_name = ldap_get(dom, "dnsRoot", str, "")
                dom_netbios_name = ldap_get(dom, "nETBIOSName", str, "")
                function_level = dom.get("msDS-Behavior-Version", -1)
                try:
                    function_level = FUNCTIONALITY_WINDOWS_VERSIONS.get(int(function_level), "")
                except Exception:
                    function_level = ""

                # Indicating wether the current domain is the root of the forest. Each forest in AD has a forest root,
                # which is the first domain that was created in the forest.
                dom_forest_root = forest_name.lower() == dom_name.lower() and dom_name != ""

                # RID's issued & remaining is very complicated since we need to contact the RID master.
                # Contacting different servers is not a thing we can do now.
                rids_issued = ""
                rids_remaining = ""

                domains_desc.append({
                    "name": dom_name,
                    "netbios_name": dom_netbios_name,
                    "function_level": function_level,
                    "forest_root": dom_forest_root,
                    "rids_issued": rids_issued,
                    "rids_remaining": rids_remaining
                })

                # Since we currently do not support contacting other servers, Domain Password Policy
                # is going to be restricted only to the current dc.
                if convert_ldap_searchpath_to_domain_name(self.domain_name).lower() == dom_name.lower():
                    domain_properties = self.get_domain_properties()
                    lockout_threshold = domain_properties.get('lockoutThreshold', '')
                    pwd_history_length = domain_properties.get('pwdHistoryLength', '')
                    max_password_age = domain_properties.get("maxPwdAge")
                    min_password_age = domain_properties.get("minPwdAge")
                    min_password_length = domain_properties.get("minPwdLength", "")

                    # Special formats
                    try:
                        max_password_age = str(format(ad_integer8_to_timedelta(max_password_age)))
                    except Exception:
                        max_password_age = ""

                    try:
                        min_password_age = str(format(ad_integer8_to_timedelta(min_password_age)))
                    except Exception:
                        min_password_age = ""

                    password_policies.append({
                        "domain_name": dom_name,
                        "domain_netbios_name": dom_netbios_name,
                        "lockout_threshold": lockout_threshold,
                        "pwd_history_length": pwd_history_length,
                        "max_password_age": max_password_age,
                        "min_password_age": min_password_age,
                        "min_password_length": min_password_length
                    })

        except Exception:
            logger.exception("error getting domains")
            domains_desc = []
            password_policies = []

        # Domain integrated DNS Zones
        logger.info("Statistics - DNS Zones")
        try:
            dns_zones = []
            dns_zones_records = list(self._ldap_search(
                "(objectClass=dnsZone)",
                search_base=self.domaindnszones_naming_context))
            dns_zones_records.extend(list(self._ldap_search(
                "(objectClass=dnsZone)",
                search_base=self.forestdnszones_naming_context)))

            for dns_zone_record in dns_zones_records:
                dn = ldap_must_get_str(dns_zone_record, 'distinguishedName')
                dns_zone_record_partition = "Domain" if "domaindnszones" in dn.lower() else "Forest"
                dns_zone_record_name = ldap_get(dns_zone_record, "name", str, "")
                dns_zone_record_created = parse_date(dns_zone_record.get("whenCreated"))
                dns_zone_record_changed = parse_date(dns_zone_record.get("whenChanged"))

                try:
                    dns_zone_record_count = len(list(self._ldap_search(
                        ("(objectClass=dnsNode)"),
                        attributes=[ldap3.NO_ATTRIBUTES],
                        search_base=dn
                    )))
                except Exception:
                    dns_zone_record_count = 0
                    logger.exception(f"couldn't get number of records in dns zone {dn}")

                dns_zones.append({
                    "domain": convert_ldap_searchpath_to_domain_name(self.domain_name),
                    "partition": dns_zone_record_partition,
                    "name": dns_zone_record_name,
                    "record_count": dns_zone_record_count,
                    "zone_record_created": dns_zone_record_created if dns_zone_record_created is not None else "",
                    "zone_record_changed": dns_zone_record_changed if dns_zone_record_changed is not None else ""
                })
        except Exception:
            dns_zones = []
            logger.exception("error parsing dns zones")

        # GPO's
        logger.info("Statistics - GPO's")
        try:
            gpo_table = []

            for gpo in self._ldap_search("(objectClass=groupPolicyContainer)"):
                gpo_name = ldap_get(gpo, "displayName", str, "")
                gpo_when_created = parse_date(gpo.get("whenCreated"))
                gpo_when_changed = parse_date(gpo.get("whenChanged"))

                gpo_table.append({
                    "name": gpo_name,
                    "when_created": gpo_when_created if gpo_when_created is not None else "",
                    "when_changed": gpo_when_changed if gpo_when_changed is not None else ""
                })
        except Exception:
            gpo_table = []
            logger.exception("error pasring gpo tables")

        # Domain Trusts
        logger.info("Statistics - Domain Trusts")
        try:
            domain_trusts = []

            for dt in self._ldap_search("(objectClass=trustedDomain)"):
                domain_trust_name = ldap_get(dt, "name", str, "")
                domain_trust_when_created = parse_date(dt.get("whenCreated"))
                domain_trust_when_changed = parse_date(dt.get("whenChanged"))

                trust_direction = ldap_get(dt, "trustDirection", int)
                trust_attributes = ldap_get(dt, "trustAttributes", int)
                trust_type = ldap_get(dt, "trustType", int)

                if trust_direction is not None:
                    domain_trust_direction = {
                        1: "Inbound",
                        2: "Outbound",
                        3: "Two-Way"
                    }.get(int(trust_direction), "")
                else:
                    domain_trust_direction = ""

                if trust_attributes is not None:
                    trust_attributes = int(trust_attributes)
                    ta = []
                    for bit_to_see, attr_to_see in TRUST_ATTRIBUTES_DICT.items():
                        if trust_attributes & bit_to_see > 0:
                            ta.append(attr_to_see)

                    domain_trust_attributes = ",".join(ta)
                else:
                    domain_trust_attributes = ""

                if trust_type is not None:
                    domain_trust_type = {
                        1: "Down level",
                        2: "Up Level",
                        3: "MIT",
                        4: "DCE"
                    }.get(int(trust_type), "")
                else:
                    domain_trust_type = ""

                domain_trusts.append({
                    "domain": convert_ldap_searchpath_to_domain_name(self.domain_name),
                    "name": domain_trust_name,
                    "direction": domain_trust_direction,
                    "attributes": domain_trust_attributes,
                    "type": domain_trust_type,
                    "created": domain_trust_when_created if domain_trust_when_created is not None else "",
                    "changed": domain_trust_when_changed if domain_trust_when_changed is not None else "",
                })

        except Exception:
            domain_trusts = []
            logger.exception("error parsing domain trusts")

        return [{
            "name": "Groups",
            "fields": [{"Group": "group_name"}, {"Count": "count"}],
            "data": [
                {"group_name": "Total Groups", "count": total_groups},
                {"group_name": "Builtin", "count": builtin},
                {"group_name": "Universal Security", "count": universal_security},
                {"group_name": "Universal Distribution", "count": universal_distribution},
                {"group_name": "Global Security", "count": global_security},
                {"group_name": "Global Distribution", "count": global_distribution},
                {"group_name": "Domain Local Security", "count": domain_local_security},
                {"group_name": "Domain Local Distribution", "count": domain_local_distribution},
            ]
        },
            {
                "name": "Forest Summary",
                "fields": [{"Name": "name"}, {"Value": "value"}],
                "data": [
                    {"name": "Name", "value": forest_name},
                    {"name": "Functional Level", "value": forest_functionality},
                    {"name": "Naming Master", "value": naming_master},
                    {"name": "Schema Master", "value": schema_master},
                    {"name": "Domain Count", "value": domains_in_forest_count},
                    {"name": "Site Count", "value": forest_sites_count},
                    {"name": "DC Server Count", "value": forest_dc_count},
                    {"name": "GC Server Count", "value": global_catalogs_count},
                    {"name": "Exchange Server Count", "value": exchange_servers_count},
                ]
        },
            {
                "name": "Forest Features",
                "fields": [{"Name": "name"}, {"Value": "value"}],
                "data": [
                    {"name": "Recycle Bin Enabled", "value": recycle_bin_enabled},
                    {"name": "Tombstone Lifetime", "value": tombstone_lifetime},
                    {"name": "Exchange Version", "value": exchange_version},
                ]
        },
            {
                "name": "Site Summary",
                "fields": [{"Name": "name"}, {"Value": "value"}],
                "data": [
                    {"name": "Site Count", "value": forest_sites_count},
                    {"name": "Site Subnet Count", "value": forest_site_subnet_count},
                    {"name": "Site Link Count", "value": forest_site_link_count},
                    {"name": "Site Connection Count", "value": forest_site_connections_count},
                    {"name": "Sites Without Site Connections", "value": forest_site_without_site_connections},
                    {"name": "Sites Without ISTG", "value": forest_sites_without_site_istg},
                    {"name": "Sites Without Subnets", "value": forest_site_without_subnets},
                    {"name": "Sites Without Servers", "value": forest_site_without_servers},
                ]
        },
            {
                "name": "Forest Site Summary",
                "fields": [
                    {"Name": "name"},
                    {"Location": "location"},
                    {"Domains": "domains"},
                    {"DCs": "dcs"},
                    {"Subnets": "subnets"}
                ],
                "data": forest_sites_summary
        },
            {
                "name": "Forest Site Details",
                "fields": [
                    {"Name": "name"},
                    {"Options": "options"},
                    {"ISTG": "istg"},
                    {"Site Links": "site_links"},
                    {"Bridgehead Servers": "bridgehead_servers"},
                    {"Adjacent Sites": "adjacent_sites"}
                ],
                "data": forest_site_details
        },
            {
                "name": "Site Subnets",
                "fields": [
                    {"Name": "name"},
                    {"Site": "site"},
                    {"Location": "location"}
                ],
                "data": forest_subnets
        },
            {
                "name": "Site Connections",
                "fields": [
                    {"Enabled": "connection_enabled"},
                    {"Options": "sc_options"},
                    {"From": "sc_from"},
                    {"To": "sc_to"}
                ],
                "data": site_connections
        },
            {
                "name": "Site Links",
                "fields": [
                    {"Name": "name"},
                    {"Replication Inteval": "repl_interval"},
                    {"Cost": "cost"},
                    {"Type": "type"},
                    {"Site List": "sitelist"},
                    {"Change Notification Enabled": "change_notification_enabled"}
                ],
                "data": site_links
        },
            {
                "name": "Domains",
                "fields": [
                    {"Name": "name"},
                    {"Netbios Name": "netbios_name"},
                    {"Function Level": "function_level"},
                    {"Forest Root": "forest_root"},
                    {"RIDs Issued": "rids_issued"},
                    {"RIDs Remaining": "rids_remaining"}
                ],
                "data": domains_desc
        },
            {
                "name": "Domain Password Policies",
                "fields": [
                    {"Domain Name": "domain_name"},
                    {"Netbios Name": "domain_netbios_name"},
                    {"Lockout Threshold": "lockout_threshold"},
                    {"Password History Length": "pwd_history_length"},
                    {"Max Password Age": "max_password_age"},
                    {"Min Password Age": "min_password_age"},
                    {"Min Password Length": "min_password_length"}
                ],
                "data": password_policies
        },
            {
                "name": "Domain Trusts",
                "fields": [
                    {"Domain Name": "domain"},
                    {"Name": "name"},
                    {"Direction": "direction"},
                    {"Attributes": "attributes"},
                    {"Type": "type"},
                    {"When Created": "created"},
                    {"When Changed": "changed"}
                ],
                "data": domain_trusts
        },
            {
                "name": "Domain Integrated DNS Zones",
                "fields": [
                    {"Domain": "domain"},
                    {"Partition": "partition"},
                    {"Name": "name"},
                    {"Record Count": "record_count"},
                    {"When Created": "zone_record_created"},
                    {"When Changed": "zone_record_changed"}
                ],
                "data": dns_zones
        },
            {
                "name": "Domain GPOs",
                "fields": [
                    {"Name": "name"},
                    {"When Created": "when_created"},
                    {"When Changed": "when_changed"}
                ],
                "data": gpo_table
        }
        ]

    # GC Relevant functions
    def gc_get_all_domains_in_forest(self):
        assert self.__connect_with_gc_mode is True, 'Must be in GC Mode'
        domains = self._ldap_search(
            '(objectClass=domain)',
            attributes=['distinguishedName'],
            search_base=''  # GC Requires empty search base.
        )
        return [convert_ldap_searchpath_to_domain_name(dn['distinguishedName']) for dn in list(domains)]
