"""LdapConnection.py: Implementation of LDAP protocol connection."""
import logging

logger = logging.getLogger(f"axonius.{__name__}")
import ssl
import ipaddress
import struct
from enum import Enum, auto

import ldap3

from active_directory_adapter.exceptions import LdapException
from axonius.utils.parsing import get_exception_string
from axonius.utils.parsing import convert_ldap_searchpath_to_domain_name
from axonius.utils.files import create_temp_file


class SSLState(Enum):
    Unencrypted = auto()
    Verified = auto()
    Unverified = auto()


LDAP_ACCOUNTDISABLE = 0x2
LDAP_DONT_EXPIRE_PASSWORD = 0x10000
LDAP_PASSWORD_NOT_REQUIRED = 0x0020

DNS_TYPE_A = 0x0001     # ivp4
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


class LdapConnection(object):
    """Class responsible for creating an ldap connection.

    This class will use a single LDAP connection in order to retrieve
    Data from the wanted ActiveDirectory.
    """

    def __init__(self, ldap_page_size, server_addr,
                 user_name, user_password, dns_server,
                 use_ssl: SSLState, ca_file_data: bytes, cert_file: bytes,
                 private_key: bytes, should_fetch_disabled_devices, should_fetch_disabled_users):
        """Class initialization.

        :param int ldap_page_size: Amount of devices to fetch on each request
        :param str server_addr: Server address (name of IP)
        :param str user_name: User name to connect with
        :param str user_password: Password
        :param str dns_server: Address of other dns server
        :param bool use_ssl: Whether or not to use ssl. If true, ca_file_data, cert_file and private_key must be set
        """
        self.server_addr = server_addr
        self.user_name = user_name
        self.user_password = user_password
        self.dns_server = dns_server
        self.ldap_connection = None
        self.ldap_page_size = ldap_page_size
        self.__use_ssl = use_ssl
        self.should_fetch_disabled_devices = should_fetch_disabled_devices
        self.should_fetch_disabled_users = should_fetch_disabled_users

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

            # Get domain configurations. The following have to be, they are critical values
            # like 'distinguishedName'.
            self.root_dse = self.get_dc_properties()
            self.domain_name = self.root_dse['defaultNamingContext']
            self.configuration_naming_context = self.root_dse['configurationNamingContext']
            self.schema_naming_context = self.root_dse['schemaNamingContext']

            if type(self.domain_name) == list:
                # This returns as a list, but according to all info in the internet its an only string
                # (a dc can't handle two domains..)
                if len(self.domain_name) != 1:
                    logger.warning(f"domain_name is not of length 1: {self.domain_name}")
                self.domain_name = self.domain_name[0]   # If this fails, its a critical problem. raise an exception.

            if type(self.configuration_naming_context) == list:
                # same - only one configuration naming context.
                if len(self.configuration_naming_context) != 1:
                    logger.warning(f"domain_name is not of length 1: {self.configuration_naming_context}")
                # If this fails, its a critical problem. raise an exception.
                self.configuration_naming_context = self.configuration_naming_context[0]

            # This is constant.
            self.domaindnszones_naming_context = f"DC=DomainDnsZones,{self.domain_name}"

            # Get the domain properties (usually contains its policy)
            self.domain_properties = self.get_domain_properties()
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
            search_base = self.domain_name

        if search_scope is None:
            search_scope = ldap3.SUBTREE

        try:
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
                    paged_size=self.ldap_page_size,
                    generator=True)

            try:
                entry_generator = ldap_paged_search()
            except ldap3.core.exceptions.LDAPException:
                # No need to do that a couple of times. There is a logic in the adapters themselves
                # that tries more times if that fails.
                self._connect_to_server()
                entry_generator = ldap_paged_search()

            for entry in entry_generator:
                if entry['type'] == 'searchResEntry':
                    yield entry['attributes']

        except ldap3.core.exceptions.LDAPException:
            raise LdapException(get_exception_string())

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

        try:
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
        except ldap3.core.exceptions.LDAPException:
            raise LdapException(get_exception_string())

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
                dn = gc_ntdsa['distinguishedName'].replace("CN=NTDS Settings,", "")

                # Now Lets query for the dnshostname of this object. This is in the config schema.
                try:
                    dns_hostname = self._ldap_search("(dnsHostName=*)",
                                                     attributes=["dnsHostName"],
                                                     search_base=dn,
                                                     search_scope=ldap3.BASE)

                    # There should always be 1 here. because its the parent of an object we already found.
                    gc_list.append(list(dns_hostname)[0]['dnsHostName'])
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
                role_owner_dn = list(query_answer)[0]['fSMORoleOwner']

                # This always starts with CN=NTDS Settings, we need the parent.
                # It has to be in this specific format.
                role_owner_dn = role_owner_dn.replace("CN=NTDS Settings,", "")

                # Now Lets query for the dnshostname of this object. This is in the config schema.
                try:
                    dns_hostname = self._ldap_search("(dnsHostName=*)",
                                                     attributes=["dnsHostName"],
                                                     search_base=role_owner_dn,
                                                     search_scope=ldap3.BASE)

                    return list(dns_hostname)[0]["dnsHostName"]
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
                dhcp_servers_list = ds.get('dhcpServers')
                if dhcp_servers_list is not None and dhcp_servers_list != "" and dhcp_servers_list != []:
                    if type(dhcp_servers_list) == str:
                        dhcp_servers_list = [dhcp_servers_list]

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
            search_base = dfsr_configuration_object[0]['distinguishedName']
        except Exception:
            search_base = f"CN=DFSR-GlobalSettings,CN=System,{self.domain_name}"

        # Get the whole subtree. We then organize it the way we want.
        dfsr_shares = dict()
        try:
            dfsr_configurations_subtree = self._ldap_search("(|(objectClass=msDFSR-ReplicationGroup)(objectClass=msDFSR-ContentSet)(objectClass=msDFSR-Member))",
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
                if "msDFSR-ReplicationGroup" in dfsr_item['objectClass']:
                    dfsr_replication_groups.append(dfsr_item)
                elif "msDFSR-ContentSet" in dfsr_item['objectClass']:
                    dfsr_content_sets.append(dfsr_item)
                elif "msDFSR-Member" in dfsr_item['objectClass']:
                    dfsr_members.append(dfsr_item)

            # build tree. dfsr shares is a dict of replication groups, with their content and servers.
            # e.g.
            # dfsr_shares = {"SHARE": {"content": ["share1", "share2"], "servers": ["dc1.testdomain.test"]}}

            for rg in dfsr_replication_groups:
                dfsr_shares[rg['cn']] = {"content": [], "servers": []}

            for content_set in dfsr_content_sets:
                # dn should look like "CN={content_name},CN=Content,CN={replication_group_name},..."
                replication_group_cn = content_set['distinguishedName'].split(",")[2][3:]
                dfsr_shares[replication_group_cn]['content'].append(content_set['cn'])

            for server in dfsr_members:
                # dn should look like "CN={member_name},CN=Topology,CN={replication_group_name},..."
                replication_group_cn = server['distinguishedName'].split(",")[2][3:]
                if "msDFSR-ComputerReference" in server:
                    dfsr_shares[replication_group_cn]['servers'].append(server['msDFSR-ComputerReference'])

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

    def get_device_list(self, should_dns_resolve_one_at_a_time):
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

        devices_generator = self._ldap_search(search_filter)

        one_device = None
        devices_count = 0
        for one_device in devices_generator:
            device_dict = dict(one_device)
            if 'userCertificate' in device_dict:
                # Special case where we want to remove 'userCertificate' key (Special case for Amdocs)
                del device_dict['userCertificate']
            device_dict['AXON_DNS_ADDR'] = self.dns_server if self.dns_server else self.server_addr
            device_dict['AXON_DC_ADDR'] = self.server_addr
            device_dict['AXON_DOMAIN_NAME'] = self.domain_name
            devices_count += 1

            # Resolve DNS if asked.
            if should_dns_resolve_one_at_a_time is True:
                device_name = device_dict.get("name") or device_dict.get("cn")
                if device_name is not None:
                    device_dict['AXON_IP_ADDRESSES'] = [ip for (host, ip) in self.get_dns_records(device_name)]

            if devices_count % 1000 == 0:
                logger.info(f"Got {devices_count} devices so far")
            yield device_dict

        if one_device is None:
            return []

    def get_users_list(self):
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

        users_generator = self._ldap_search(search_filter)
        users_count = 0
        for user in users_generator:
            user['axonius_extended'] = {"maxPwdAge": self.domain_properties['maxPwdAge']}

            users_count = users_count + 1
            if users_count % 100 == 0:
                logger.info(f"Got {users_count} users so far")

            yield dict(user)

    def get_dns_records(self, name=None):
        """
        Returns dns records for this zone.
        :param name: optional. if exists, will query only for a specific hostname. note! this should be the name
                     of the record, e.g. "WINXP", not "WINXP.TestDomain.test".
        :return: yields (name, ip_addr) where name is string and ip_addr is ipv4/ipv6 object from the ipaddress module.
        """

        try:
            if name is None:
                search_query = f"(&(objectClass=dnsNode)" \
                               f"(|(dnsRecord={IPV4_ENTRY_PREFIX}*)(dnsRecord={IPV6_ENTRY_PREFIX}*)))"
            else:
                search_query = f"(&(objectClass=dnsNode)(name={name})" \
                               f"(|(dnsRecord={IPV4_ENTRY_PREFIX}*)(dnsRecord={IPV6_ENTRY_PREFIX}*)))"

            # The dns records for this particular domain reside in "DomainDnsZones.[Domain_DN]".
            dns_records = self._ldap_search(search_query,
                                            attributes=['dnsRecord', 'name'],
                                            search_base="DC={0},CN=MicrosoftDNS,{1}".format(
                                                convert_ldap_searchpath_to_domain_name(self.domain_name),
                                                self.domaindnszones_naming_context))

            dns_record_i = 0
            for dns_record in dns_records:
                try:
                    # Parse binary format.
                    dns_record_binary = dns_record['dnsRecord']
                    if type(dns_record_binary) == str:
                        # Some objects can have multiple ip's. for example, a computer that has ipv4 and ivp6 addr.
                        # so sometimes you get a list and sometimes not.
                        dns_record_binary = [dns_record_binary]

                    for record_binary in dns_record_binary:
                        # the binary format is as follows:
                        # https://msdn.microsoft.com/en-us/library/ee898781.aspx
                        # since i want only "type" , which is the third and fourth byte, i'm handling the rest
                        # as padding (X).

                        dns_record_i += 1
                        if dns_record_i % 500 == 0:
                            logger.info(f"Brought {dns_record_i} dns records already")

                        record_type = struct.unpack("<2xH19x", record_binary[:23])[0]

                        # This can be ipv4 or ipv6 object.

                        if record_type == DNS_TYPE_A or record_type == DNS_TYPE_AAAA:
                            # ip_address can get a big-endian bytes object. ip_address automatically
                            # understands if its in ipv4 or ipv6 at creates the appropriate object.
                            ip_addr = ipaddress.ip_address(record_binary[24:])
                            yield (dns_record['name'], str(ip_addr))

                except Exception:
                    logger.exception(f"Error in parsing dns record {dns_record}")

            if name is None:
                # We brought many dns records.
                logger.info(f"Finished Yielding {dns_record_i} dns records.")

                # If we were asked to bring the whole zone but didn't bring anythign..
                if dns_record_i == 0:
                    logger.warning(f"Didn't bring any DNS Record! do we have this zone? try chainging "
                                   f"search_base to only self.domaindnszones_naming_context to search the whole dns")
        except Exception:
            logger.exception("exception while querying dns")
            return []

    def get_extended_devices_list(self, should_dns_resolve_one_at_a_time):
        """
        Returns a lot of information about devices.
        :return:
        """

        d = dict()
        d['devices'] = self.get_device_list(should_dns_resolve_one_at_a_time)
        d['printers'] = self.get_printers_list()
        d['dfsr_shares'] = self.get_dfsr_shares()
        d['sites'] = self.get_sites()   # subnets are part of sites so no need for extended subnets config
        d['dhcp_servers'] = self.get_dhcp_servers()
        d['fsmo_roles'] = self.get_fsmo_roles()
        d['global_catalogs'] = self.get_global_catalogs()
        d['exchange_servers'] = self.get_exchange_servers()

        # If we want to resolve one at a time, we shouldn't get all dns records.
        d['dns_records'] = self.get_dns_records() if should_dns_resolve_one_at_a_time is False else []

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

        user_account_control = entity[0]['userAccountControl']

        if enabled:
            new_user_account_control = user_account_control & (~LDAP_ACCOUNTDISABLE)
        else:
            new_user_account_control = user_account_control | LDAP_ACCOUNTDISABLE

        logger.info(
            f"Changing entity {distinguished_name} state from {user_account_control} to {new_user_account_control}")

        return self._ldap_modify(distinguished_name, {"userAccountControl": new_user_account_control})
