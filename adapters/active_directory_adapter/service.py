import ipaddress
import json
import logging
import os
import os.path
import subprocess
import tempfile
import threading
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional, Iterator

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger

from active_directory_adapter.consts import LDAP_FIELD_TO_EXCLUDE_CONFIG
from active_directory_adapter.execution import ActiveDirectoryExecutionMixIn
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import (ClientConnectionException,
                                        TagDeviceError)
from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.clients.ldap.exceptions import (IpResolveError, LdapException,
                                             NoClientError)
from axonius.clients.ldap.ldap_connection import (LDAP_ACCOUNTDISABLE, LDAP_ACCOUNT_LOCKOUT,
                                                  LdapConnection,
                                                  DEFAULT_LDAP_RECIEVE_TIMEOUT,
                                                  DEFAULT_LDAP_CONNECTION_TIMEOUT,
                                                  DEFAULT_LDAP_PAGE_SIZE, AD_GC_PORT_ENCRYPTED, AD_GC_PORT,
                                                  AD_LDAP_PORT, AD_LDAPS_PORT)
from axonius.consts.adapter_consts import (DEVICES_DATA, DNS_RESOLVE_STATUS,
                                           IPS_FIELDNAME,
                                           NETWORK_INTERFACES_FIELDNAME)
from axonius.devices import ad_entity
from axonius.devices.ad_entity import ADEntity
from axonius.devices.device_adapter import DeviceAdapter
from axonius.devices.dns_resolvable import (DNSResolvableDevice,
                                            DNSResolveStatus)
from axonius.fields import Field, JsonStringFormat, ListField
from axonius.mixins.configurable import Configurable
from axonius.mixins.devicedisabelable import Devicedisabelable
from axonius.mixins.userdisabelable import Userdisabelable
from axonius.plugin_base import add_rule, return_error
from axonius.smart_json_class import SmartJsonClass
from axonius.types.ssl_state import SSLState, COMMON_SSL_CONFIG_SCHEMA_CA_ONLY
from axonius.users.user_adapter import UserAdapter
from axonius.utils.networking import check_if_tcp_port_is_open
from axonius.utils.datetime import parse_date, is_date_real
from axonius.utils.dns import query_dns, async_query_dns_list
from axonius.utils.entity_finder import EntityFinder
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import (ad_integer8_to_timedelta,
                                   bytes_image_to_base64,
                                   convert_ldap_searchpath_to_domain_name,
                                   format_ip, get_exception_string,
                                   get_first_object_from_dn,
                                   get_member_of_list_from_memberof,
                                   get_organizational_units_from_dn,
                                   parse_bool_from_raw)
from axonius.utils.ssl import get_ca_bundle

logger = logging.getLogger(f'axonius.{__name__}')

TEMP_FILES_FOLDER = "/home/axonius/temp_dir/"

LDAP_DONT_EXPIRE_PASSWORD = 0x10000
LDAP_PASSWORD_NOT_REQUIRED = 0x0020

# Note! After this time the process will be terminated. We shouldn't ever terminate a process while it runs,
# In case its the execution we might leave some files on the target machine which is a bad idea.
# For exactly this reason we have another mechanism to reject execution promises on the execution-requester side.
# This value should be for times we are really really sure there is a problem.
MAX_SUBPROCESS_TIMEOUT_FOR_EXEC_IN_SECONDS = 60 * 60 * 1  # 1 hour
RESOLVE_CHANGE_STATUS_INTERVAL = 60 * 60 * 1  # 1 hour


# TODO ofir: Change the return values protocol
class AvailableIp(SmartJsonClass):
    """ A definition for the json-schema for an available IP and its origin"""
    ip = Field(str, 'IP', converter=format_ip, json_format=JsonStringFormat.ip)
    source_dns = Field(str, 'DNS server that gave the result')


class AvailableIps(SmartJsonClass):
    available_ips = ListField(AvailableIp, "Map between IPs and their origin")


class ADPrinter(SmartJsonClass):
    """ A definition for an active directory printer"""

    name = Field(str, "Printer Name")
    description = Field(str, "Printer Description")
    server_name = Field(str, "Printer Server Name")
    share_name = Field(str, "Printer Share Name")
    location_name = Field(str, "Printer Location")
    driver_name = Field(str, "Printer Driver Name")


class ADDfsrShare(SmartJsonClass):
    """ A definition for a domain DFSR Share"""

    name = Field(str, "Name")
    content = ListField(str, "Content")


class ActiveDirectoryAdapter(Userdisabelable, Devicedisabelable, ActiveDirectoryExecutionMixIn, AdapterBase,
                             Configurable):
    DEFAULT_LAST_SEEN_THRESHOLD_HOURS = None
    DEFAULT_LAST_FETCHED_THRESHOLD_HOURS = 48
    DEFAULT_USER_LAST_SEEN = 24 * 365 * 5
    DEFAULT_LAST_SEEN_PRIORITIZED = True

    class MyDeviceAdapter(DeviceAdapter, DNSResolvableDevice, ADEntity):
        ad_service_principal_name = ListField(str, "AD Service Principal Name")
        ad_printers = ListField(ADPrinter, "AD Attached Printers")
        ad_dfsr_shares = ListField(ADDfsrShare, "AD DFSR Shares")
        ad_dc_source = Field(str, 'AD DC Source')
        ms_mcs_adm_pwd = Field(str, 'Mc Mcs Admin Pwd')
        ms_mcs_adm_pwd_expiration_time = Field(datetime, 'Mc Mcs Admin Pwd Expiration Time')
        is_laps_installed = Field(bool, 'Is LAPS Installed')
        resolvable_hostname = ListField(str, 'Resolvable Hostnames')

    class MyUserAdapter(UserAdapter, ADEntity):
        ad_service_principal_name = ListField(str, "AD Service Principal Name")
        user_managed_objects = ListField(str, "AD User Managed Objects")
        user_account_control = Field(int, 'User Account Control')
        account_lockout = Field(bool, "Account Lockout")
        ad_dc_source = Field(str, 'AD DC Source')
        mobile = Field(str, 'Mobile Number')
        company = Field(str, 'Company')
        company_code = Field(str, 'Company Code')
        cost_center = Field(str, 'Cost Center')
        cost_center_description = Field(str, 'Cost Center Description')
        division = Field(str, 'Division')
        division_code = Field(str, 'Division Code')
        se_business_role = Field(str, 'SE Business Role')
        se_business_unit_name = Field(str, 'SE Business Unit Name')
        sw_hw_segment = Field(str, 'SE HW Segment')
        se_job_code = Field(str, 'SE Job Code')
        se_guid_manager = Field(str, 'SE guid_manager')
        se_department_role_title = Field(str, 'SE Department Role Title')
        se_sub_functional_area = Field(str, 'SE Sub Functional Area')
        director_two = Field(str, 'Director Two')
        location = Field(str, 'Location')
        vice_president = Field(str, 'Vice President')

    def __init__(self):

        # Initialize the base plugin (will initialize http server)
        super().__init__(get_local_config_file(__file__))

        self._resolving_thread_lock = threading.RLock()

        self.__devices_data_db = self._get_collection(DEVICES_DATA)
        executors = {'default': ThreadPoolExecutor(3)}
        self._background_scheduler = LoggedBackgroundScheduler(executors=executors)

        # Thread for resolving IP addresses of devices
        self._background_scheduler.add_job(func=self._resolve_hosts_addr_thread,
                                           trigger=IntervalTrigger(minutes=2),
                                           next_run_time=datetime.now(),
                                           name='resolve_host_thread',
                                           id='resolve_host_thread',
                                           max_instances=1)
        # Thread for resetting the resolving process
        self._background_scheduler.add_job(func=self._resolve_change_status_thread,
                                           trigger=IntervalTrigger(
                                               seconds=RESOLVE_CHANGE_STATUS_INTERVAL),  # Every 1 hour
                                           next_run_time=datetime.now(),
                                           name='change_resolve_status_thread',
                                           id='change_resolve_status_thread',
                                           max_instances=1)

        # Thread for inserting reports. Start in 30 minutes to allow the system to initialize
        # and especially the clients themselves -> it might take a couple of seconds to connect.

        # Currently the reports from AD are disabled.
        #  self._background_scheduler.add_job(func=self.generate_report,
        #                                   trigger=IntervalTrigger(minutes=self.__report_generation_interval),
        #                                   next_run_time=datetime.now() + timedelta(seconds=30),
        #                                   name='report_generation_thread',
        #                                   id='report_generation_thread',
        #                                   max_instances=1
        #                                   )

        self._background_scheduler.start()

        # create temp files dir
        os.makedirs(TEMP_FILES_FOLDER, exist_ok=True)
        # TODO: Weiss: Ask why not using temp file to create dir.

    @add_rule('generate_report_now', methods=['POST'], should_authenticate=False)
    def generate_report_now(self):
        # Currently we do not want the AD report to be shown in the executive report
        return ''
        jobs = self._background_scheduler.get_jobs()
        report_generation_thread_job = next(job for job in jobs if job.name == 'report_generation_thread')
        report_generation_thread_job.modify(next_run_time=datetime.now())
        self._background_scheduler.wakeup()

        return ''

    def generate_report(self):
        """
        Generates a report about this adapter. This usually means getting data (in a specific format defined
        by the reporting mechanism of the gui) that isn't device-centralized, e.g. all subnets in the network.
        :return:
        """
        try:
            time_needed = datetime.now()
            d = {}
            for client_name, client_data in self._clients.copy().items():
                logger.info(f"Starting Statistics Report for client {client_name}")
                cd = client_data.get_session("reports")
                cd.reconnect()
                d[client_name] = cd.get_report_statistics()

            update_result = self._get_collection("report").update_one({"name": "report"},
                                                                      {
                                                                          "$set": {
                                                                              "name": "report",
                                                                              "date": datetime.now(),
                                                                              "data": d
                                                                          }
            }, upsert=True)

            time_needed = datetime.now() - time_needed
            logger.info(f"Statistics end (took {time_needed}), modified {update_result.modified_count} document in db")
        except Exception:
            self._get_collection("report").delete({"name": "report"})
            logger.exception("Exception while generating report")

    def _on_config_update(self, config):
        logger.info(f"Loading AD config: {config}")
        self.__dns_query_chunk_size = config['dns_chunk_size']
        self.__sync_resolving = False
        self.__resolving_enabled = config['resolving_enabled']
        self.__report_generation_interval = 30
        self.__fetch_users_image = config.get('fetch_users_image', True)
        self.__should_get_nested_groups_for_user = config.get('should_get_nested_groups_for_user', True)
        self.__add_ip_conflict = False
        self.__ldap_page_size = config.get('ldap_page_size', DEFAULT_LDAP_PAGE_SIZE)
        self.__ldap_connection_timeout = config.get('ldap_connection_timeout', DEFAULT_LDAP_CONNECTION_TIMEOUT)
        self.__ldap_recieve_timeout = config.get('ldap_recieve_timeout', DEFAULT_LDAP_RECIEVE_TIMEOUT)
        self.__ldap_field_to_exclude = config.get('ldap_field_to_exclude') or []
        self.__ldap_sensitive_fields_to_exclude = config.get('ldap_sensitive_fields_to_exclude') or ''
        self.__verbose_auth_notifications = config.get('verbose_auth_notifications') or False

        # Change interval of report generation thread
        try:
            jobs = self._background_scheduler.get_jobs()
            report_generation_thread_job = next(job for job in jobs if job.name == 'report_generation_thread')
            report_generation_thread_job.reschedule(trigger=IntervalTrigger(minutes=self.__report_generation_interval))
        except Exception:
            # Current design calls _on_config_update from Configurable, which is initialized before this class's
            # init is called. so _background_scheduler isn't there yet, and an AttributeError is thrown.
            # This is why i catch this legitimate error.
            pass

    @property
    def _python_27_path(self):
        return self.config['paths']['python_27_path']

    @property
    def _use_wmi_smb_path(self):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), self.config['paths']['wmi_smb_path']))

    def _get_client_id(self, dc_details):
        return dc_details['dc_name']

    def _test_reachability(self, client_config):
        connect_with_gc_mode = client_config.get('is_ad_gc') or False
        use_ssl = SSLState[client_config.get('use_ssl', SSLState.Unencrypted.name)]
        if connect_with_gc_mode:
            port = AD_GC_PORT if use_ssl == SSLState.Unencrypted else AD_GC_PORT_ENCRYPTED
        else:
            port = AD_LDAP_PORT if use_ssl == SSLState.Unencrypted else AD_LDAPS_PORT

        return check_if_tcp_port_is_open(client_config['dc_name'], port)

    def _get_ldap_connection(self, dc_details):
        ca_file_data = None
        if dc_details.get('ca_file'):
            ca_file_data = self._grab_file_contents(dc_details.get('ca_file'))
        else:
            ca_file_data = get_ca_bundle()

        ldap_connection_timeout = None
        if self.__ldap_connection_timeout is not None:
            ldap_connection_timeout = self.__ldap_connection_timeout

        ldap_recieve_timeout = None
        if self.__ldap_recieve_timeout is not None:
            ldap_recieve_timeout = self.__ldap_recieve_timeout

        return LdapConnection(dc_details['dc_name'],
                              dc_details['user'],
                              dc_details['password'],
                              dc_details.get('dns_server_address'),
                              self.__ldap_page_size,
                              SSLState[dc_details.get('use_ssl', SSLState.Unencrypted.name)],
                              ca_file_data,
                              self._grab_file_contents(dc_details.get('cert_file')),
                              self._grab_file_contents(dc_details.get('private_key')),
                              dc_details.get('fetch_disabled_devices', False),
                              dc_details.get('fetch_disabled_users', False),
                              ldap_connection_timeout=ldap_connection_timeout,
                              ldap_recieve_timeout=ldap_recieve_timeout,
                              connect_with_gc_mode=dc_details.get('is_ad_gc', False),
                              ldap_ou_whitelist=dc_details.get('ldap_ou_whitelist'),
                              alternative_dns_suffix=dc_details.get('alternative_dns_suffix'),
                              do_not_fetch_users=dc_details.get('do_not_fetch_users')
                              )

    def _connect_client(self, dc_details):
        message = ''
        try:
            success_domains = {}
            all_domains = {}
            failure_domains = {}
            dc = self._get_ldap_connection(dc_details)
            if dc.is_in_gc_mode:
                # This is a request by the user to connect to a DC which is a GC, and get all domains in forest.
                for found_domain in dc.gc_get_all_domains_in_forest():
                    try:
                        logger.info(f'GC: Found {found_domain}')
                        found_dc_details = dc_details.copy()
                        found_dc_details['dc_name'] = found_domain
                        found_dc_details['is_ad_gc'] = False
                        all_domains[found_domain.lower()] = found_dc_details
                        if not success_domains:
                            # Try to add at least one domain.
                            success_domains[found_domain.lower()] = self._get_ldap_connection(found_dc_details)
                    except Exception as e:
                        logger.exception(f'Problem adding dc found by gc: {found_domain}: '
                                         f'{get_exception_string(force_show_traceback=True)}')
                        failure_domains[found_domain.lower()] = str(e)

                if not success_domains:
                    if len(failure_domains) > 0:
                        raise ClientConnectionException(
                            f'can not connect in GC mode: {list(failure_domains.values())[0]}'
                        )
                    else:
                        raise ClientConnectionException(f'did not find any server in the GC.')

            else:
                # This is the normal path where a user simply puts a domain.
                all_domains[dc_details['dc_name'].lower()] = dc_details
            return all_domains
        except LdapException as e:
            if 'certificate verify failed' in str(e).lower():
                additional_msg = 'Certificate Verification Failed'
            elif "socket connection error while opening: timed out" in str(e).lower():
                additional_msg = "connection timed out"
            elif "saslprep error:" in str(e).lower():
                additional_msg = "Invalid credentials - credentials contain invalid characters"
            elif 'ldapstrongerauthrequiredresult' in str(e).lower():
                additional_msg = 'Server requires a stronger authentication. Please try using an encrypted connection'
            elif 'ldapinvalidcredentialsresult' in str(e).lower():
                if 'data 52e' in str(e).lower():
                    additional_msg = 'Invalid credentials'
                elif 'data 525' in str(e).lower():
                    additional_msg = 'User not found (AcceptSecurityContext error, data 525)'
                elif 'data 530' in str(e).lower():
                    additional_msg = 'Not permitted to logon at this time (AcceptSecurityContext error, data 530)'
                elif 'data 531' in str(e).lower():
                    additional_msg = 'Not permitted to logon from ' \
                                     'this workstation (AcceptSecurityContext error, data 531)'
                elif 'data 532' in str(e).lower():
                    additional_msg = 'Password expired (AcceptSecurityContext error, data 532)'
                elif 'data 533' in str(e).lower():
                    additional_msg = 'Account disabled (AcceptSecurityContext error, data 533)'
                elif 'data 701' in str(e).lower():
                    additional_msg = 'Account expired (AcceptSecurityContext error, data 701)'
                elif 'data 773' in str(e).lower():
                    additional_msg = 'User must reset password (AcceptSecurityContext error, data 773)'
                elif 'data 775' in str(e).lower():
                    additional_msg = 'Account locked out (AcceptSecurityContext error, data 775)'
                elif 'data 51f' in str(e).lower():
                    additional_msg = 'The LDAP connector/server is in an overloaded state ' \
                                     '(AcceptSecurityContext error, data 51f)'
                else:
                    if 'AcceptSecurityContex' in str(e):
                        try:
                            additional_msg = f'Invalid Credentials: {str(e)[str(e).find("AcceptSecurityContex"):]}'
                        except Exception:
                            additional_msg = f'Invalid credentials: {str(e)}'
                    else:
                        additional_msg = f'Invalid credentials: {str(e)}'
            elif 'socket ssl wrapping error' in str(e).lower():
                additional_msg = 'SSL error. Please check the SSL settings'
            elif 'invalid server address' in str(e).lower():
                additional_msg = f'Invalid server address - {str(e)}'
            else:
                additional_msg = f'connection error, please check the settings - {str(e)}'
            message = f'Error: {additional_msg}.'
            logger.exception(message)
        except ClientConnectionException as e:
            raise ClientConnectionException(f'Error: {str(e)}')
        except Exception:
            ex_str = get_exception_string(force_show_traceback=True)
            message = f'Error - please check your credentials: {ex_str}'
            logger.exception(f'Error in _connect_client: {ex_str}')
        raise ClientConnectionException(message)

    def _clients_schema(self):
        """
        The keys AdAdapter expects from configs.abs
        :return: json schema
        """
        return {
            "items": [
                {
                    "name": "dc_name",
                    "title": "DC Address",
                    "type": "string"
                },
                {
                    "name": "user",
                    "title": "Username (DOMAIN\\USERNAME)",
                    "type": "string"
                },
                {
                    "name": "password",
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                },
                {
                    "name": "dns_server_address",
                    "title": "DNS Server Address",
                    "type": "string"
                },
                {
                    'name': 'alternative_dns_suffix',
                    'title': 'Alternative DNS suffix',
                    'description': 'Alternative DNS suffix to append to hosts for ip resolving',
                    'type': 'string'
                },
                *COMMON_SSL_CONFIG_SCHEMA_CA_ONLY,
                {
                    'name': 'do_not_fetch_users',
                    'title': 'Do Not Fetch Users',
                    'type': 'bool'
                },
                {
                    "name": "fetch_disabled_devices",
                    "title": "Fetch Disabled Devices",
                    "type": "bool"
                },
                {
                    "name": "fetch_disabled_users",
                    "title": "Fetch Disabled Users",
                    "type": "bool"
                },
                {
                    'name': 'is_ad_gc',
                    'title': 'Connect to Global Catalog (GC)',
                    'type': 'bool'
                },
                {
                    'name': 'ldap_ou_whitelist',
                    'title': 'Organizational units whitelist',
                    'description': 'List of OU names to fetch entities from',
                    'type': 'array',
                    'items': {
                        'type': 'string'
                    }
                }
            ],
            "required": [
                "dc_name",
                "user",
                "password",
                'do_not_fetch_users',
                'fetch_disabled_devices',
                'fetch_disabled_users',
                'is_ad_gc'
            ],
            "type": "array"
        }

    def _resolve_clients(self, client_data_dict, should_verbose_notify=False):
        success_clients = dict()
        failure_clients = dict()
        for client_name, client_data_dict_val in client_data_dict.items():
            try:
                logger.info(f'Trying to connect to {client_name}')
                success_clients[client_name] = self._get_ldap_connection(client_data_dict_val)
            except Exception as e:
                logger.exception(f'Can not connect to {client_name}')
                failure_clients[client_name] = str(e)

        if self.__verbose_auth_notifications and should_verbose_notify:
            content = ''
            for failure_client, failure_reason in failure_clients.items():
                content += f'{failure_client}: {failure_reason}\n\n'
            self.create_notification(
                f'Active Directory Adapter: {len(success_clients)} / {len(client_data_dict.values())} '
                f'successful connections',
                content=content
            )

        if not success_clients:
            raise ClientConnectionException(f'Could not connect to any of the clients')

        return success_clients

    def _resolve_client_from_client_dict_and_entity(self, client_data, entity_data):
        client_data_dict = None
        try:
            client_data_dict = client_data[entity_data['ad_dc_source'].lower()]
        except Exception:
            pass

        try:
            if not client_data_dict:
                client_data_dict = client_data[entity_data['raw']['AXON_DC_ADDR'].lower()]
        except Exception:
            pass

        if not client_data_dict:
            # If its not here then crash since we couldn't get the device client
            client_data_dict = \
                client_data[convert_ldap_searchpath_to_domain_name(entity_data['raw']['distinguishedName']).lower()]

        return self._get_ldap_connection(client_data_dict)

    def _query_devices_by_client(self, client_name, client_data_dict: Dict[str, dict]):
        """
        Get all devices from a specific Dc

        :param str client_name: The name of the client
        :param str client_data: The data of the client

        :return: iter(dict) with all the attributes returned from the DC per client
        """
        success_clients = self._resolve_clients(client_data_dict, should_verbose_notify=True)
        try:
            domain_nbns_to_dns = dict()
            for client_name, client_data in success_clients.items():
                try:
                    domain_nbns_to_dns.update(client_data.get_domain_prefix_to_dns_dict())
                except Exception:
                    logger.exception(f'{client_name}: Error getting nbns to dns translation table, passing')

            if domain_nbns_to_dns:
                current_table = self.get_global_keyval('ldap_nbns_to_dns') or {}
                current_table.update(domain_nbns_to_dns)
                logger.info(f'Updating domain nbns to dns to: {current_table}')
                self.set_global_keyval('ldap_nbns_to_dns', current_table)

        except Exception:
            logger.exception(f'Can not get nbns to dns translation table - generic! passing')

        for client_name, client_data in success_clients.items():
            try:
                if self.__ldap_page_size is not None:
                    client_data.set_ldap_page_size(self.__ldap_page_size)

                if self.__ldap_connection_timeout is not None:
                    client_data.set_ldap_connection_timeout(self.__ldap_connection_timeout)

                if self.__ldap_recieve_timeout is not None:
                    client_data.set_ldap_recieve_timeout(self.__ldap_recieve_timeout)

                client_data.reconnect()
                yield client_name, client_data.get_extended_devices_list()
            except Exception:
                logger.exception(f'Could not fetch devices from {client_name}')

    def _query_users_by_client(self, client_name, client_data_dict: Dict[str, dict]):
        """
        Get a list of users from a specific DC.

        :param client_name: The name of the client
        :param client_data: The data of the client.
        :return:
        """
        success_clients = self._resolve_clients(client_data_dict)

        for client_name, client_data in success_clients.items():
            try:
                client_data.reconnect()
                yield client_name, client_data.get_users_list(
                    should_get_nested_groups_for_user=self.__should_get_nested_groups_for_user
                )
            except Exception:
                logger.exception(f'Could not fetch users from {client_name}')

    def _parse_generic_ad_raw_data(self, ad_entity: ADEntity, raw_data: dict):
        """
        Both ad device and ad user has a lot in common. We parse them here.
        :param ad_entity: the entity to add things to.
        :param raw_data: the raw data for this entity
        :return:
        """

        ad_entity.ad_sid = raw_data.get("objectSid")
        ad_entity.ad_guid = raw_data.get("objectGUID")
        ad_entity.ad_name = raw_data.get("name")
        ad_entity.ad_sAMAccountName = raw_data.get("sAMAccountName")
        ad_entity.ad_display_name = raw_data.get("displayName")
        ad_entity.ad_distinguished_name = raw_data.get("distinguishedName")
        ad_entity.ad_account_expires = parse_date(raw_data.get("accountExpires"))
        ad_entity.ad_object_class = [i.lower() for i in raw_data.get("objectClass")]
        ad_entity.ad_object_category = raw_data.get("objectCategory")
        ad_entity.ad_organizational_unit = get_organizational_units_from_dn(raw_data.get("distinguishedName"))
        ad_entity.ad_last_logoff = parse_date(raw_data.get("lastLogoff"))
        ad_entity.ad_last_logon = parse_date(raw_data.get("lastLogon"))
        ad_entity.ad_last_logon_timestamp = parse_date(raw_data.get("lastLogonTimestamp"))
        ad_entity.ad_bad_password_time = parse_date(raw_data.get("badPasswordTime"))
        ad_entity.ad_bad_pwd_count = raw_data.get("badPwdCount")
        ad_entity.ad_password_last_set = parse_date(raw_data.get("pwdLastSet"))
        ad_entity.ad_cn = raw_data.get("cn")
        ad_entity.ad_usn_changed = raw_data.get("uSNChanged")
        ad_entity.ad_usn_created = raw_data.get("uSNCreated")
        ad_entity.ad_when_changed = parse_date(raw_data.get("whenChanged"))
        ad_entity.ad_when_created = parse_date(raw_data.get("whenCreated"))
        ad_entity.ad_is_critical_system_object = parse_bool_from_raw(raw_data.get("isCriticalSystemObject"))
        try:
            ad_entity.ad_member_of = get_member_of_list_from_memberof(raw_data.get("memberOf"))
        except Exception:
            pass
        ad_entity.ad_managed_by = get_first_object_from_dn(raw_data.get('managedBy'))
        ad_entity.ad_msds_allowed_to_delegate_to = raw_data.get("msDS-AllowedToDelegateTo")
        ad_entity.ad_canonical_name = raw_data.get('canonicalName')
        ad_entity.figure_out_dial_in_policy(raw_data.get('msNPAllowDialin'))
        ad_entity.figure_out_delegation_policy(raw_data.get("userAccountControl"),
                                               raw_data.get("msDS-AllowedToDelegateTo"))
        ad_entity.ad_last_dc_fetched = raw_data.get('AXON_CURRENT_CONNECTED_DC')

        try:
            ad_entity.extension_attribute_1 = raw_data.get('extensionAttribute1')
            ad_entity.extension_attribute_2 = raw_data.get('extensionAttribute2')
            ad_entity.extension_attribute_3 = raw_data.get('extensionAttribute3')
            ad_entity.extension_attribute_4 = raw_data.get('extensionAttribute4')
            ad_entity.extension_attribute_5 = raw_data.get('extensionAttribute5')
            ad_entity.extension_attribute_6 = raw_data.get('extensionAttribute6')
            ad_entity.extension_attribute_7 = raw_data.get('extensionAttribute7')
            ad_entity.extension_attribute_8 = raw_data.get('extensionAttribute8')
            ad_entity.extension_attribute_9 = raw_data.get('extensionAttribute9')
            ad_entity.extension_attribute_10 = raw_data.get('extensionAttribute10')
            ad_entity.extension_attribute_11 = raw_data.get('extensionAttribute11')
            ad_entity.extension_attribute_12 = raw_data.get('extensionAttribute12')
            ad_entity.extension_attribute_13 = raw_data.get('extensionAttribute13')
            ad_entity.extension_attribute_14 = raw_data.get('extensionAttribute14')
            ad_entity.extension_attribute_15 = raw_data.get('extensionAttribute15')
            ad_entity.extension_attribute_16 = raw_data.get('extensionAttribute16')
            ad_entity.extension_attribute_17 = raw_data.get('extensionAttribute17')
            ad_entity.extension_attribute_18 = raw_data.get('extensionAttribute18')
            ad_entity.extension_attribute_19 = raw_data.get('extensionAttribute19')
            ad_entity.extension_attribute_1_date = parse_date(raw_data.get('extensionAttribute1'), dayfirst=True)
            ad_entity.extension_attribute_2_date = parse_date(raw_data.get('extensionAttribute2'), dayfirst=True)
            ad_entity.extension_attribute_3_date = parse_date(raw_data.get('extensionAttribute3'), dayfirst=True)
            ad_entity.extension_attribute_4_date = parse_date(raw_data.get('extensionAttribute4'), dayfirst=True)
            ad_entity.extension_attribute_5_date = parse_date(raw_data.get('extensionAttribute5'), dayfirst=True)
            ad_entity.extension_attribute_6_date = parse_date(raw_data.get('extensionAttribute6'), dayfirst=True)
            ad_entity.extension_attribute_7_date = parse_date(raw_data.get('extensionAttribute7'), dayfirst=True)
            ad_entity.extension_attribute_8_date = parse_date(raw_data.get('extensionAttribute8'), dayfirst=True)
            ad_entity.extension_attribute_9_date = parse_date(raw_data.get('extensionAttribute9'), dayfirst=True)
            ad_entity.extension_attribute_10_date = parse_date(raw_data.get('extensionAttribute10'), dayfirst=True)
            ad_entity.extension_attribute_11_date = parse_date(raw_data.get('extensionAttribute11'), dayfirst=True)
            ad_entity.extension_attribute_12_date = parse_date(raw_data.get('extensionAttribute12'), dayfirst=True)
            ad_entity.extension_attribute_13_date = parse_date(raw_data.get('extensionAttribute13'), dayfirst=True)
            ad_entity.extension_attribute_14_date = parse_date(raw_data.get('extensionAttribute14'), dayfirst=True)
            ad_entity.extension_attribute_15_date = parse_date(raw_data.get('extensionAttribute15'), dayfirst=True)
            ad_entity.extension_attribute_16_date = parse_date(raw_data.get('extensionAttribute16'), dayfirst=True)
            ad_entity.extension_attribute_17_date = parse_date(raw_data.get('extensionAttribute17'), dayfirst=True)
            ad_entity.extension_attribute_18_date = parse_date(raw_data.get('extensionAttribute18'), dayfirst=True)
            ad_entity.extension_attribute_19_date = parse_date(raw_data.get('extensionAttribute19'), dayfirst=True)
        except Exception:
            logger.exception(f'Could not parse extension attributes')

        ad_primary_group_dn = None
        try:
            pgid = raw_data.get('primaryGroupID')
            if pgid:
                if isinstance(pgid, list):
                    pgid = pgid[0]
                ad_entity.ad_primary_group_id = int(pgid)
                ad_primary_group_dn = raw_data.get('primary_group_name')
                ad_entity.ad_primary_group_dn = ad_primary_group_dn
        except Exception:
            logger.exception(f'Problem parsing primary group id')
        if raw_data.get('msDS-ResultantPSO'):
            ad_entity.ad_msds_resultant_pso = raw_data.get('msDS-ResultantPSO')

        # full member of
        try:
            ad_entity.ad_member_of_full = get_member_of_list_from_memberof(
                (raw_data.get('axonius_extended') or {}).get('member_of_full')
            )
        except Exception:
            logger.exception(f'Exception while parsing user groups')

        try:
            if ad_primary_group_dn:
                ad_primary_group_dn_nice = get_member_of_list_from_memberof([ad_primary_group_dn])
                if ad_primary_group_dn_nice:
                    ad_primary_group_dn_nice = ad_primary_group_dn_nice[0]
                    if ad_primary_group_dn_nice not in ad_entity.ad_member_of:
                        ad_entity.ad_member_of.append(ad_primary_group_dn_nice)
                    if ad_primary_group_dn_nice not in ad_entity.ad_member_of_full:
                        ad_entity.ad_member_of_full.append(ad_primary_group_dn_nice)
        except Exception:
            logger.exception(f'Can not add ad primary group dn')

        # If pwdLastSet is 0 (which is, in date time, 1/1/1601) then it means the password must change now.
        # is_date_real checks if the date is a "special" date like 1/1/1601 and if it is - the date is not real,
        # which means its 0.
        ad_entity.ad_pwd_must_change = is_date_real(raw_data.get("pwdLastSet")) is False

        ad_entity.parse_user_account_control(raw_data.get("userAccountControl"))

        ad_entity.physical_delivery_office_name = raw_data.get('physicalDeliveryOfficeName')
        ad_entity.delivery_office_name = raw_data.get('DeliveryOfficeName')

    def _parse_users_raw_data(self, client_data_result_dict: dict):
        for client_data_name, client_data_result in client_data_result_dict:
            try:
                yield from self._parse_users_raw_data_client(client_data_result)
            except Exception:
                logger.exception(f'Exception while yielding users from client data {client_data_name}')

    def _parse_users_raw_data_client(self, raw_data):
        """
        Gets raw data and yields User objects.
        :param user_raw_data: the raw data we get.
        :return:
        """
        parsed_users_ids = []
        for user_raw in raw_data:
            try:
                if self.__ldap_sensitive_fields_to_exclude:
                    for sensitive_field_to_exclude in self.__ldap_sensitive_fields_to_exclude.split(','):
                        user_raw.pop(sensitive_field_to_exclude.strip(), None)
            except Exception:
                logger.exception(f'Could not exclude sensitive fields')
            try:
                user = self._new_user_adapter()

                self._parse_generic_ad_raw_data(user, user_raw)

                username = user_raw.get("sAMAccountName")
                domain = user_raw.get("distinguishedName")
                if username is None:
                    logger.error(f"Error, could not get sAMAccountName for user.username, "
                                 f"which is mandatory. Bypassing. raw_data: {user_raw}")
                    continue

                if domain is None:
                    logger.error(f"Error, could not get distinguishedName for user.domain, "
                                 f"which is mandatory. Bypassing. raw_data: {user_raw}")
                    continue

                domain_name = convert_ldap_searchpath_to_domain_name(domain)
                if domain_name == "":
                    logger.error(f"Error, domain name turned out to be empty. Do we have DC=? its {domain}. Bypassing")
                    continue
                user.username = username
                user.ad_dc_source = user_raw.get('AXON_DC_ADDR')
                user.description = user_raw.get('description')
                user.domain = domain_name
                user.id = f"{username}@{domain_name}"  # Should be the unique identifier of that user.
                if user.id in parsed_users_ids:
                    continue
                parsed_users_ids.append(user.id)
                service_principal_name = user_raw.get("servicePrincipalName")
                if not isinstance(service_principal_name, list):
                    service_principal_name = [str(service_principal_name)]
                user.ad_service_principal_name = service_principal_name

                user.user_sid = user_raw.get('objectSid')
                user.mail = user_raw.get("mail")
                user.organizational_unit = get_organizational_units_from_dn(user_raw.get('distinguishedName'))
                user.ad_user_principal_name = user_raw.get("userPrincipalName")
                ad_member_of = get_member_of_list_from_memberof(user_raw.get("memberOf"))
                is_admin = False
                if isinstance(ad_member_of, list):
                    for ad_group in ad_member_of:
                        if isinstance(ad_group, str):
                            if ad_group.split('.')[0].lower() == 'domain admins':
                                is_admin = True
                user.is_admin = is_admin
                user.is_local = False
                user.ad_admin_count = user_raw.get("adminCount")\
                    if isinstance(user_raw.get("adminCount"), int) else None
                use_timestamps = []  # Last usage times
                user.account_expires = parse_date(user_raw.get("accountExpires"))
                user.last_bad_logon = parse_date(user_raw.get("badPasswordTime"))
                pwd_last_set = parse_date(user_raw.get("pwdLastSet"))
                if is_date_real(pwd_last_set):
                    user.last_password_change = pwd_last_set
                    # parse maxPwdAge
                    try:
                        max_pwd_age = user_raw.get("axonius_extended", {}).get("maxPwdAge")
                        if max_pwd_age is not None:
                            password_expiration_date = pwd_last_set + ad_integer8_to_timedelta(max_pwd_age)
                            user.password_expiration_date = password_expiration_date
                            user.days_until_password_expiration = \
                                (password_expiration_date.replace(tzinfo=None) - datetime.utcnow()).days
                    except Exception:
                        # This will happen for every user. Switched to debug to avoid spam
                        logger.debug(f"Error parsing max pwd age {max_pwd_age}, is it too large?")
                last_logoff = parse_date(user_raw.get("lastLogoff"))
                if is_date_real(last_logoff):
                    user.last_logoff = last_logoff
                    use_timestamps.append(last_logoff)

                last_logon = parse_date(user_raw.get("lastLogon"))
                if is_date_real(last_logon):
                    user.last_logon = last_logon
                    use_timestamps.append(last_logon)

                last_logon_timestamp = parse_date(user_raw.get("lastLogonTimestamp"))
                if is_date_real(last_logon_timestamp):
                    user.last_logon_timestamp = last_logon_timestamp
                    use_timestamps.append(last_logon_timestamp)

                user.user_created = parse_date(user_raw.get("whenCreated"))

                user.logon_count = user_raw.get("logonCount")

                # Last seen is the latest timestamp of use we have.
                use_timestamps = sorted(use_timestamps, reverse=True)
                if len(use_timestamps) > 0:
                    user.last_seen = use_timestamps[0]

                lockout_time = user_raw.get("lockoutTime")
                if is_date_real(lockout_time):
                    user.is_locked = True
                    user.last_lockout_time = parse_date(lockout_time)
                else:
                    user.is_locked = False

                # Parse the bit-field that is called userAccountControl.
                # For future reference: the list of all bits is here
                # http://jackstromberg.com/2013/01/useraccountcontrol-attributeflag-values/
                user_account_control = user_raw.get("userAccountControl")
                if user_account_control is not None and type(user_account_control) == int:
                    user.user_account_control = user_account_control
                    user.password_never_expires = bool(user_account_control & LDAP_DONT_EXPIRE_PASSWORD)
                    user.password_not_required = bool(user_account_control & LDAP_PASSWORD_NOT_REQUIRED)
                    user.account_disabled = bool(user_account_control & LDAP_ACCOUNTDISABLE)
                    user.account_lockout = bool(user_account_control & LDAP_ACCOUNT_LOCKOUT)

                # I'm afraid this could cause exceptions, lets put it in try/except.
                try:
                    thumbnail_photo = user_raw.get("thumbnailPhoto") or \
                        user_raw.get("exchangePhoto") or \
                        user_raw.get("jpegPhoto") or \
                        user_raw.get("photo") or \
                        user_raw.get("thumbnailLogo")
                    if thumbnail_photo is not None:
                        if type(thumbnail_photo) == list:
                            thumbnail_photo = thumbnail_photo[0]  # I think this can happen from some reason..
                        if len(thumbnail_photo) > 1024 * 1024:
                            # We can not afford an image that is more than 1mb.
                            for attr in ['thumbnailPhoto', 'exchangePhoto', 'jpegPhoto', 'photo', 'thumbnailLogo']:
                                user_raw.pop(attr, None)
                        elif self.__fetch_users_image:
                            user.image = bytes_image_to_base64(thumbnail_photo)
                except Exception:
                    logger.exception(f"Exception while setting thumbnailPhoto for user {user.id}.")

                # User Personal Details
                user.user_title = user_raw.get("title")
                user.user_department = user_raw.get("department")
                user.user_manager = get_first_object_from_dn(user_raw.get("manager"))
                user.user_managed_objects = user_raw.get("managedObjects")
                user.user_telephone_number = user_raw.get("telephoneNumber")
                user.user_country = user_raw.get("co")
                user.first_name = user_raw.get('givenName')
                user.last_name = user_raw.get('sn')
                user.employee_id = user_raw.get('employeeID')
                user.employee_number = user_raw.get('employeeNumber')
                user.employee_type = user_raw.get('employeeType')
                user.mobile = user_raw.get('mobile')
                try:
                    user.company = user_raw.get('company')
                    user.company_code = user_raw.get('companyCode')
                    user.cost_center = user_raw.get('costCenter')
                    user.cost_center_description = user_raw.get('costCenterDescription')
                    user.division = user_raw.get('division')
                    user.division_code = user_raw.get('divisionCode')
                    user.se_business_role = user_raw.get('sEbusinessRole')
                    user.se_business_unit_name = user_raw.get('sEbusinessUnitName')
                    user.sw_hw_segment = user_raw.get('sEHWSegment')
                    user.se_job_code = user_raw.get('sEjobCode')
                    user.se_guid_manager = user_raw.get('sEguidManager')
                    if user_raw.get('sEdepartment'):
                        user.user_department = user_raw.get('sEdepartment')
                    user.se_department_role_title = user_raw.get('sEdepartmentRoleTitle')
                    user.se_sub_functional_area = user_raw.get('sEsubFunctionalArea')
                    user.director_two = user_raw.get('cwDirectorTwo')
                    user.location = user_raw.get('cwLocation')
                    user.vice_president = user_raw.get('cwVicePresident')
                except Exception:
                    logger.exception(f'Problem adding extra fields')
                user.set_raw(user_raw)
                yield user
            except Exception:
                logger.exception(f"Exception while parsing user {user_raw.get('distinguishedName')}, bypassing")

    def _resolve_hosts_addresses(self, hosts: Iterator[dict], timeout: float = 2) -> Iterator[dict]:
        """
        Resolve a list of hosts
        :param hosts: hosts to resolve
        :param timeout: dns request timeout (seconds_
        :return: resolved hosts
        """
        i = 0
        resolve_hosts = []
        for host in hosts:
            resolvable_hostname = host.get('resolvable_hostname')
            if resolvable_hostname:
                if isinstance(resolvable_hostname, list):
                    host['hostname'] = resolvable_hostname
                else:
                    host['hostname'] = [str(resolvable_hostname)]
            else:
                host['hostname'] = [str(host.get('hostname'))]

            if host.get('AXON_DNS_ADDR'):
                nameservers = [x.strip() for x in host.get('AXON_DNS_ADDR').split(',')]
            else:
                nameservers = []
            nameservers.extend([host.get('AXON_DC_ADDR'), None])
            host['nameservers'] = nameservers
            resolve_hosts.append(host)
            i += 1
            if i % self.__dns_query_chunk_size == 0:
                logger.debug(f'DNS Requesting hosts {i}')
                for host_data, response in zip(resolve_hosts, async_query_dns_list(resolve_hosts, timeout, True)):
                    yield self.handle_dns_response(host_data, response)
                resolve_hosts = []
        # resolve all the remaining hosts
        if resolve_hosts:
            for host_data, response in zip(resolve_hosts, async_query_dns_list(resolve_hosts, timeout, True)):
                yield self.handle_dns_response(host_data, response)

    def handle_dns_response(self, host, response):
        """
        Handle hosts dns query responses
        :param host: resolved hostname
        :param response: dns query results
        :return: resolved host dict
        """
        current_resolved_host = dict(host)
        if response:
            ips_and_dns_servers = response
            ips = [ip for ip, _ in ips_and_dns_servers]
            ips = list(set(ips))  # make it unique

            current_resolved_host[IPS_FIELDNAME] = ips
            current_resolved_host[DNS_RESOLVE_STATUS] = DNSResolveStatus.Resolved.name
            try:
                if self.__add_ip_conflict:
                    available_ips = {ip: dns for ip, dns in ips_and_dns_servers}
                    if len(available_ips) > 1:
                        # If we have more than one key in available_ips that means
                        # that this device got two different IP's
                        # i.e duplicate! we need to tag this device
                        logger.debug(f"Found ip conflict. details: {str(available_ips)} on {host['id']}")
                        self.devices.add_label([(self.plugin_unique_name, host['id'])], "IP Conflicts")

                        serialized_available_ips = AvailableIps(
                            available_ips=[AvailableIp(ip=ip, source_dns=dns)
                                           for ip, dns in available_ips.items()]
                        )
                        self.devices.add_data([(self.plugin_unique_name, host['id'])], "IP Conflicts",
                                              serialized_available_ips.to_dict())
                    else:
                        # no conflicts - let's reflect that
                        self.devices.add_label([(self.plugin_unique_name, host['id'])], "IP Conflicts", False)
                        self.devices.add_data([(self.plugin_unique_name, host['id'])], "IP Conflicts", False)
            except TagDeviceError:
                pass  # if the device wasn't yet inserted this will be raised
            except Exception:
                logger.exception("Exception while checking for DNS conflicts")
        else:
            # Don't log here, it will happen for every failed resolving (Can happen a lot of times)
            current_resolved_host = dict(host)
            current_resolved_host[IPS_FIELDNAME] = []
            current_resolved_host[DNS_RESOLVE_STATUS] = DNSResolveStatus.Failed.name
        return current_resolved_host

    def _resolve_hosts_addr_thread(self):
        """ Thread for ip resolving of devices.
        This thread will try to resolve IP's of known devices.
        """
        if self.__resolving_enabled is False:
            logger.debug("Resolve Hosts Addr Thread: Resolving is disabled, not continuing")
            return

        with self._resolving_thread_lock:
            pending_filter = {DNS_RESOLVE_STATUS: DNSResolveStatus.Pending.name}
            hosts_count = self.__devices_data_db.count_documents(pending_filter)
            hosts = self.__devices_data_db.find(pending_filter,
                                                projection={'_id': True,
                                                            'id': True,
                                                            'AXON_DNS_ADDR': True,
                                                            'AXON_DC_ADDR': True,
                                                            'hostname': True,
                                                            'resolvable_hostname': True})

            logger.debug(f"Going to resolve for {hosts_count} hosts")

            did_one_resolved = False

            for resolved_host in self._resolve_hosts_addresses(hosts):
                if resolved_host.get(IPS_FIELDNAME) is not None:
                    if resolved_host[DNS_RESOLVE_STATUS] == DNSResolveStatus.Resolved.name:
                        did_one_resolved = True
                    self.__devices_data_db.update_one(
                        {"_id": resolved_host["_id"]},
                        {'$set':
                         {IPS_FIELDNAME: resolved_host[IPS_FIELDNAME],
                          DNS_RESOLVE_STATUS: resolved_host[DNS_RESOLVE_STATUS]}
                         }
                    )

            if not did_one_resolved and hosts_count != 0:
                # Raise log message only if no host could get resolved
                logger.debug("Couldn't resolve IP's. Maybe dns is incorrect?")
            return

    def _resolve_change_status_thread(self):
        """ This thread is responsible for restarting the name resolving process
        """
        if self.__resolving_enabled is False:
            logger.debug("Resolve Change Status Thread: Resolving is disabled, not continuing")
            return

        with self._resolving_thread_lock:
            hosts_count = self.__devices_data_db.count_documents({DNS_RESOLVE_STATUS: DNSResolveStatus.Pending.name},
                                                                 limit=2)
            if hosts_count == 0:
                self.__devices_data_db.update_many({}, {'$set': {DNS_RESOLVE_STATUS:
                                                                 DNSResolveStatus.Pending.name}})
            return

    @add_rule('resolve_ip', methods=['POST'], should_authenticate=False)
    def resolve_ip_now(self):
        jobs = self._background_scheduler.get_jobs()
        reset_job = next(job for job in jobs if job.name == 'change_resolve_status_thread')
        reset_job.modify(next_run_time=datetime.now())
        self._background_scheduler.wakeup()
        resolve_job = next(job for job in jobs if job.name == 'resolve_host_thread')
        resolve_job.modify(next_run_time=datetime.now())
        self._background_scheduler.wakeup()
        return ''

    def __parse_exchange_servers(self, exchange_servers_raw_data):
        try:
            if exchange_servers_raw_data is None:
                exchange_servers_raw_data = []
            exchange_servers = {es['cn'].lower(): es for es in exchange_servers_raw_data}
        except Exception:
            exchange_servers = {}
            logger.exception(f"Exception while parsing exchange servers {exchange_servers_raw_data}. Continuing")

        return exchange_servers

    def __parse_dfsr_shares(self, dfsr_shares_raw_data):
        try:
            dfsr_shares_by_dn = defaultdict(list)
            if dfsr_shares_raw_data is None:
                dfsr_shares_raw_data = []

            for dfsr_replication_group_name, dfsr_replication_group_inner in dfsr_shares_raw_data:
                # "content" and "servers" are things that are defined in LdapConnection, they are always present.
                content = dfsr_replication_group_inner['content']
                servers = dfsr_replication_group_inner['servers']

                for server in servers:
                    if type(server) == str:
                        dfsr_shares_by_dn[server.lower()].append(
                            ADDfsrShare(name=dfsr_replication_group_name, content=content))
        except Exception:
            dfsr_shares_by_dn = {}
            logger.exception(f"Exception while pasring dfsr shares {dfsr_shares_raw_data}. Continuing")

        return dfsr_shares_by_dn

    def __parse_fsmo_roles(self, fsmo_roles_raw_data):
        fsmo_roles = {}
        try:
            for role, server in fsmo_roles_raw_data.items():
                fsmo_roles[role] = server.lower()
        except Exception:
            logger.exception(f"Error while parsing FSMO shares {fsmo_roles_raw_data}. Continuing")

        return fsmo_roles

    def __parse_global_catalogs(self, global_catalogs_raw_data):
        try:
            global_catalogs = [gc.lower() for gc in global_catalogs_raw_data]
        except Exception:
            global_catalogs = []
            logger.exception(f"Error while parsing global catalogs {global_catalogs_raw_data}. Continuing")

        return global_catalogs

    def __parse_dhcp_servers(self, dhcp_servers_raw_data):
        try:
            dhcp_servers = [dhcp_server.lower() for dhcp_server in dhcp_servers_raw_data]
        except Exception:
            dhcp_servers = []
            logger.exception(f"Error while parsing dhcp servers {dhcp_servers_raw_data}. Continuing")

        return dhcp_servers

    def __parse_dns_records(self, dns_records_raw_data):
        dns_records = {}
        try:
            if dns_records_raw_data is None:
                dns_records_raw_data = []
            for (name, ip) in dns_records_raw_data:
                dns_records[name.lower()] = ip
        except Exception:
            logger.exception(f"Error while parsing dns records {dns_records_raw_data}. Continuing")

        return dns_records

    def __parse_sites_and_subnets(self, sites_raw_data):
        sites_and_subnets = []
        try:
            if sites_raw_data is None:
                sites_raw_data = []
            for site in sites_raw_data:
                subnets = site.get("siteObjectBL")
                if type(subnets) == list:
                    for subnet_raw in subnets:
                        # its a dn. e.g. 'CN=192.168.20.0/24,CN=Subnets,CN=Sites...'
                        try:
                            subnet = ipaddress.ip_network(subnet_raw.split(",")[0][3:])  # [3:] to remove "CN="
                            sites_and_subnets.append((subnet, site.get("name"), site.get("location")))
                        except Exception:
                            logger.exception(f"Exception parsing subnet {subnet_raw}.")
        except Exception:
            logger.exception(f"Error while parsing sites and subnets {sites_raw_data}. Continuing")

        return sites_and_subnets

    def __parse_printers(self, printers_raw_data):
        try:
            if printers_raw_data is None:
                printers_raw_data = []

            printers_raw_dict = defaultdict(list)
            for printer_raw in printers_raw_data:
                dn = printer_raw.get("shortServerName")
                if dn is not None:
                    printers_raw_dict[dn].append(printer_raw)
                else:
                    logger.error(f"Found printer without shortServerName: {printer_raw}")
        except Exception:
            printers_raw_dict = []
            logger.exception(f"Error while parsing printers {printers_raw_data}. Continuing")

        return printers_raw_dict

    def _parse_raw_data(self, client_data_result_dict: dict):
        for client_data_name, client_data_result in client_data_result_dict:
            try:
                yield from self._parse_raw_data_client(client_data_result)
            except Exception:
                logger.exception(f'Exception while yielding devices from client data {client_data_name}')

    def _parse_raw_data_client(self, extended_devices_list):
        devices_raw_data = extended_devices_list['devices']

        # Note that we have to convert all hostnames to lower since ldap sometimes returns them in their
        # original form, but sometimes it lowers them.

        exchange_servers = self.__parse_exchange_servers(extended_devices_list['exchange_servers'])
        dfsr_shares_by_dn = self.__parse_dfsr_shares(extended_devices_list['dfsr_shares'])
        fsmo_roles = self.__parse_fsmo_roles(extended_devices_list['fsmo_roles'])
        global_catalogs = self.__parse_global_catalogs(extended_devices_list['global_catalogs'])
        dhcp_servers = self.__parse_dhcp_servers(extended_devices_list['dhcp_servers'])
        dns_records = self.__parse_dns_records(extended_devices_list['dns_records'])
        sites_and_subnets = self.__parse_sites_and_subnets(extended_devices_list['sites'])
        printers_raw_dict = self.__parse_printers(extended_devices_list['printers'])

        # DNS Resolving - active thread
        dns_resolved_devices_collection = self.__devices_data_db
        dns_resolved_devices_db = dns_resolved_devices_collection.find(
            {},
            projection={'_id': False, 'id': True, IPS_FIELDNAME: True, DNS_RESOLVE_STATUS: True}
        )
        dns_resolved_devices_db = {device['id']: device for device in dns_resolved_devices_db}
        dns_resolving_devices_to_insert_to_db = []
        no_timestamp_count = 0

        # Now, Lets parse the devices
        if devices_raw_data is None:
            devices_raw_data = []

        parsed_devices_ids = []
        for device_raw in devices_raw_data:
            try:
                if self.__ldap_sensitive_fields_to_exclude:
                    for sensitive_field_to_exclude in self.__ldap_sensitive_fields_to_exclude.split(','):
                        device_raw.pop(sensitive_field_to_exclude.strip(), None)
            except Exception:
                logger.exception(f'Could not exclude sensitive fields')
            try:
                last_logon = device_raw.get('lastLogon')
                last_logon_timestamp = device_raw.get('lastLogonTimestamp')

                last_seen = None
                if last_logon is not None and last_logon_timestamp is not None:
                    try:
                        last_seen = max(last_logon, last_logon_timestamp)
                    except Exception:
                        if isinstance(last_logon, datetime):
                            last_seen = last_logon
                        elif isinstance(last_logon_timestamp, datetime):
                            last_seen = last_logon_timestamp
                else:
                    last_seen = last_logon or last_logon_timestamp

                if last_seen is None or is_date_real(last_seen) is False:
                    # No data on the last timestamp of the device. Not inserting this device.
                    # This can happen quite a lot so we don't print any message.
                    last_seen = None
                    no_timestamp_count += 1

                device = self._new_device_adapter()
                if self.__ldap_field_to_exclude:
                    ad_object_category = device_raw.get('objectCategory') or ''
                    if isinstance(ad_object_category, str) and ad_object_category.strip():
                        ad_object_category = ad_object_category.strip()
                        if any(item.strip() and item.strip() in ad_object_category
                               for item in self.__ldap_field_to_exclude):
                            logger.debug(f'Skipping device {device_raw.get("distinguishedName")}, excluded')
                            continue

                device.ad_dc_source = device_raw.get('AXON_DC_ADDR')
                self._parse_generic_ad_raw_data(device, device_raw)
                try:
                    device.ms_mcs_adm_pwd = device_raw.get('msMcsAdmPwd')
                    device.ms_mcs_adm_pwd_expiration_time = parse_date(device_raw.get('msMcsAdmPwdExpirationTime'))
                    device.is_laps_installed = True if device_raw.get('ms-Mcs-AdmPwdExpirationTime') else False
                except Exception:
                    logger.exception(f'Problem adding msmcs stuff')
                device.description = device_raw.get('description')
                device.network_interfaces = []
                device.last_seen = last_seen
                device.dns_resolve_status = DNSResolveStatus.Pending
                device.id = device_raw['distinguishedName']
                if device.id in parsed_devices_ids:
                    continue
                parsed_devices_ids.append(device.id)
                device_domain = convert_ldap_searchpath_to_domain_name(device_raw['distinguishedName'])
                device.domain = device_domain
                if device_domain:
                    # If we do not have dNSHostName than we would like to create it using name and domain.
                    device.hostname = device_raw.get('dNSHostName',
                                                     f"{device_raw.get('name', '')}.{str(device_domain)}")
                else:
                    device.hostname = device_raw.get('dNSHostName', device_raw.get('name', ''))
                device.name = device_raw.get('name')
                alternative_dns_suffix = device_raw.get('alternative_dns_suffix')
                resolvable_hostnames = []
                if alternative_dns_suffix:
                    resolvable_hostname_prefix = device.hostname.rstrip(device_domain)
                    for dns_suffix in alternative_dns_suffix.split(','):
                        resolvable_hostnames.append(resolvable_hostname_prefix + '.' + dns_suffix.strip().lstrip('.'))
                else:
                    resolvable_hostnames.append(device.hostname)
                device.resolvable_hostname = resolvable_hostnames
                device.part_of_domain = True
                device.organizational_unit = get_organizational_units_from_dn(device.id)
                service_principal_name = device_raw.get("servicePrincipalName")  # only for devices
                if not isinstance(service_principal_name, list):
                    service_principal_name = [str(service_principal_name)]
                device.ad_service_principal_name = service_principal_name  # only for devices

                # OS. we must change device.os only after figure_os which initializes it
                device.figure_os(device_raw.get('operatingSystem', ''))
                device.os.build = device_raw.get('operatingSystemVersion')
                try:
                    build = device.os.build
                    if '(' in build and ')' in build:
                        device.os.build = build.split('(')[1].split(')')[0]
                except Exception:
                    pass
                device.os.sp = device_raw.get('operatingSystemServicePack')

                device.device_managed_by = get_first_object_from_dn(device_raw.get('managedBy'))

                user_account_control = device_raw.get("userAccountControl")
                if user_account_control is not None and type(user_account_control) == int:
                    device.device_disabled = bool(user_account_control & LDAP_ACCOUNTDISABLE)

                    # Is this a Domain Controller? If so, parse some more things
                    if user_account_control == (ad_entity.TRUSTED_FOR_DELEGATION | ad_entity.SERVER_TRUST_ACCOUNT) \
                            or "OU=Domain Controllers" in device_raw['distinguishedName']:
                        device.ad_is_dc = True

                        hostname_lower = device_raw.get('dNSHostName', '').lower()
                        device.ad_dc_gc = hostname_lower in global_catalogs
                        device.ad_dc_infra_master = fsmo_roles['infra_master'] == hostname_lower
                        device.ad_dc_rid_master = fsmo_roles['rid_master'] == hostname_lower
                        device.ad_dc_pdc_emulator = fsmo_roles['pdc_emulator'] == hostname_lower
                        device.ad_dc_naming_master = fsmo_roles['naming_master'] == hostname_lower
                        device.ad_dc_schema_master = fsmo_roles['schema_master'] == hostname_lower

                        device.ad_dc_is_dhcp_server = hostname_lower in dhcp_servers

                        # Registered NPS Servers are part of "RAS and IAS Servers" group.
                        device.ad_dc_is_nps_server = any(["ras and ias servers" in mo.lower()
                                                          for mo in device.ad_member_of])
                    else:
                        device.ad_is_dc = False

                # parse dfsr shares
                device.ad_dfsr_shares = dfsr_shares_by_dn.get(device_raw['distinguishedName'].lower())

                # Add all printers associated to this device
                device_raw_cn = device_raw.get("cn")
                if device_raw_cn is not None and device_raw_cn in printers_raw_dict:
                    # printers_raw_dict is a (key, value) dict where key is a server (device) cn
                    # and the value is a list of printers that are associated to it.
                    # so printers_raw_dict[some_device_cn] will give the list of printers that are
                    # associated to it.
                    for printer_raw in printers_raw_dict[device_raw_cn]:
                        device.ad_printers.append(ADPrinter(
                            name=printer_raw.get("printerName"),
                            description=printer_raw.get("description"),
                            server_name=printer_raw.get("serverName"),
                            share_name=printer_raw.get("printShareName"),
                            location_name=printer_raw.get("location"),
                            driver_name=printer_raw.get("driverName")
                        ))

                # Is it an exchange server?
                if device_raw_cn is not None and device_raw_cn.lower() in exchange_servers:
                    try:
                        exchange_server_info = exchange_servers[device_raw_cn.lower()]
                        device_raw["exchange_server_info"] = exchange_server_info

                        device.ad_is_exchange_server = True

                        # Parse organization and admin group. distinguished name always looks like:
                        # CN=[cn],CN=Servers,CN=[admin group],CN=Administrative Groups,CN=[org name]
                        distinguished_name_groups = [dn[3:]
                                                     for dn in exchange_server_info["distinguishedName"].split(",")]
                        device.ad_exchange_server_admin_group = distinguished_name_groups[2]
                        device.ad_exchange_server_organization = distinguished_name_groups[4]
                        device.ad_exchange_server_name = exchange_server_info.get("name")
                        device.ad_exchange_server_serial = exchange_server_info.get("serialNumber")
                        device.ad_exchange_server_product_id = exchange_server_info.get("msExchProductID")

                        exchange_server_roles = exchange_server_info.get("msExchCurrentServerRoles")
                        if exchange_servers is not None:
                            device.figure_out_exchange_server_roles(exchange_server_roles)
                    except Exception:
                        logger.exception("problem while parsing is exchange server. continuing")

                else:
                    device.ad_is_exchange_server = False

                # Get all ip's known to us from the ip search thread
                ips_list = []

                # Its better to find_one each time then getting the whole table into the memory.
                device_interfaces = dns_resolved_devices_db.get(device_raw['distinguishedName'])
                if device_interfaces is not None:
                    ips_list = device_interfaces.get(IPS_FIELDNAME, [])
                    device.dns_resolve_status = DNSResolveStatus[device_interfaces[DNS_RESOLVE_STATUS]]
                else:
                    device_as_dict = device.to_dict()
                    # Instead of putting the whole device (this will result in a huge number of devices inserted)
                    # Lets just put whats important
                    device_as_dict_for_resolving = {
                        "id": device_as_dict['id'],
                        "hostname": device_as_dict['hostname'],
                        'resolvable_hostname': device_as_dict.get('resolvable_hostname'),
                        "AXON_DNS_ADDR": device_raw['AXON_DNS_ADDR'],
                        "AXON_DC_ADDR": device_raw['AXON_DC_ADDR'],
                        "dns_resolve_status": device_as_dict['dns_resolve_status']
                    }

                    if self.__sync_resolving and self.__resolving_enabled is True \
                            and not self._is_adapter_old_by_last_seen(device_as_dict):
                        device.network_interfaces = []
                        for resolved_device in self._resolve_hosts_addresses([device_as_dict_for_resolving]):
                            if resolved_device[DNS_RESOLVE_STATUS] == DNSResolveStatus.Resolved.name:
                                ips_list = resolved_device[IPS_FIELDNAME]
                                device.dns_resolve_status = DNSResolveStatus[resolved_device[DNS_RESOLVE_STATUS]]

                    # Note that we always need to put devices into our db, since the rest of the code (like wmi exec)
                    # uses this db to understand if this device is resolvable.

                    if not self._is_adapter_old_by_last_seen(device_as_dict):
                        # That means that the device is new (As determined in adapter_base code)
                        dns_resolving_devices_to_insert_to_db.append(device_as_dict_for_resolving)

                        # optimization in memory
                        if len(dns_resolving_devices_to_insert_to_db) >= 1000:
                            dns_resolved_devices_collection.insert_many(dns_resolving_devices_to_insert_to_db)
                            dns_resolving_devices_to_insert_to_db = []

                # Lets add ip's from ldap.
                # note that i want it to be the last one. this is, becuase, in the next loop we are
                # going to parse subnet and site. if for some reason there are multiple associations,
                # the last one will be the result.
                if device.ad_name.lower() in dns_records:
                    ip = dns_records[device.ad_name.lower()]
                    if ip not in ips_list:
                        ips_list.append(ip)

                # ips_list is a list. Make it unique, if somehow it inclues the same ip's.
                ips_list = list(set(ips_list))

                # Try to resolve the subnet and site location by the list of ip's.
                # Note that we assume that the list of ip's here will reflect only one subnet (== site).
                # In case there are multiple subnets that affect multiple sites - we can't know how to associate.
                subnets_list = []
                for ip in ips_list:
                    try:
                        for (subnet, site_name, site_location) in sites_and_subnets:
                            if ipaddress.ip_address(ip) in subnet:
                                device.ad_site_name = site_name
                                device.ad_site_location = site_location
                                device.ad_subnet = str(subnet)

                                subnets_list.append(str(subnet))
                    except Exception:
                        logger.exception("Exception in ip to subnet parsing. Might be an ipv6 ip, continuing..")

                # make the subnets list unique
                subnets_list = list(set(subnets_list))
                device.add_nic(ips=ips_list, subnets=subnets_list)

                device.adapter_properties = [AdapterProperty.Assets.name, AdapterProperty.Manager.name]
                device.set_raw(device_raw)

                yield device
            except Exception:
                logger.exception(f"Exception when parsing device {device_raw.get('distinguishedName')}, bypassing")
        if len(dns_resolving_devices_to_insert_to_db) > 0:
            dns_resolved_devices_collection.insert_many(dns_resolving_devices_to_insert_to_db)
        if no_timestamp_count != 0:
            logger.warning(f"Got {no_timestamp_count} with no timestamp while parsing data")

    def _create_random_file(self, file_buffer, attrib='w'):
        """ Creating a random file in the temp_file folder.

        :param bytes file_buffer: The buffer of the file we want to save
        :param string attrib: The attributes for the 'open' command

        :return string: The name of the file created
        """
        (file_handle_os, os_path) = tempfile.mkstemp(
            suffix='.tmp', dir=TEMP_FILES_FOLDER)

        with os.fdopen(file_handle_os, attrib) as file_obj:
            # Using `os.fdopen` converts the handle to an object that acts like a
            # regular Python file object, and the `with` context manager means the
            # file will be automatically closed when we're done with it.
            file_obj.write(file_buffer)
            return os_path

    def _resolve_device_name(self, device_name, client_config, timeout=2) -> List[Tuple[str, str]]:
        """ Resolve a device name address using dns servers.
        This function will first try to resolve IP using the machine network interface DNS servers.
        If the servers cant find an appropriate IP, The function will try to query the DC (assuming that it
        is also a DNS server).

        :param dict device_name: The name of the device to resolve
        :param dict client_config:  Client data. Must contain 'dc_name'
        :param int timeout: The timeout for the dns query process. Since we try twice the function ca block
                            up to 3*timeout seconds
        :return: List of Tuple[ip, dns_origin]
        :raises exception.IpResolveError: In case of an error in the query process
        """
        # We are assuming that the dc is the DNS server
        if isinstance(device_name, list):
            full_device_name = device_name
        else:
            full_device_name = [str(device_name)]

        err = f"Resolving {str(full_device_name)} of {client_config['dc_name']} "

        ips = []

        for full_dn in full_device_name:
            try:
                dns_server = None
                ips.append((query_dns(full_dn, timeout, dns_server), 'default'))
            except Exception as e:
                err += f"failed to resolve host {full_dn} from {dns_server} <{e}>; "

            try:
                dns_server = client_config["dns_server_address"]
                for dns_server in (client_config.get("dns_server_address") or '').split(','):
                    ips.append((query_dns(full_dn, timeout, dns_server.strip()), dns_server.strip()))
            except Exception as e:
                err += f"failed to resolve host {full_dn}  from {dns_server} <{e}>; "

            try:
                dns_server = client_config["dc_name"]
                ips.append((query_dns(full_dn, timeout, dns_server), dns_server))
            except Exception as e:
                err += f"failed to resolve host {full_dn} from {dns_server} <{e}>; "

        if ips:
            return ips

        raise IpResolveError(err)

    def _get_basic_wmi_smb_command(self, device_data, custom_credentials: dict = None):
        """ Function for formatting the base wmiqery command.

        :param dict device_data: The device_data used to create this command
        :return string: The basic command
        """
        clients_config = self._get_clients_config()
        wanted_client = device_data['client_used']
        for client_config in clients_config:
            client_config = client_config['client_config']
            if client_config["dc_name"] == wanted_client:
                client_config = self._normalize_password_fields(client_config)
                # If wmi/smb user was not supplied, use the default one.
                client_username = custom_credentials.get("username") if custom_credentials else None
                if client_username is None or client_username == "":
                    client_username = client_config['user']

                # If wmi/smb password was not supplied, use the default one.
                client_password = custom_credentials.get("password") if custom_credentials else None
                if client_password is None or client_password == "":
                    client_password = client_config['password']

                # We have found the correct client. Getting credentials
                if '\\' in client_username:
                    domain_name, user_name = client_username.split('\\')
                else:
                    # This is a legitimate flow. Do not try to build the domain name from the configurations.
                    domain_name, user_name = "", client_username

                wanted_hostname = device_data['data'].get('resolvable_hostname') or device_data['data']['hostname']
                password = client_password
                try:
                    # We resolve ip only for devices who have been resolved before.
                    # We do this to reduce the time execution tasks take for devices that we are sure
                    # will not be resolved.
                    device_ip, _ = self._resolve_device_name(wanted_hostname, client_config)[0]
                except Exception:
                    logger.exception(f"Exception - could not resolve ip for execution.")
                    raise

                # Putting the file using wmi_smb_path.
                return [self._python_27_path, self._use_wmi_smb_path, domain_name, user_name, password, device_ip,
                        "//./root/cimv2"]
        raise NoClientError()  # Couldn't find an appropriate client

    def put_files(self, device_data, files_path, files_content, custom_credentials=None):
        """
        puts a list of files.
        :param device_data: the device data.
        :param files_path: a list of paths, e.g. ["c:\\a.txt"]
        :param files_content: a list of files content.
        :return:
        """

        commands_list = []
        for fp, fc in zip(files_path, files_content):
            commands_list.append({"type": "putfile", "args": [fp, fc]})

        return self.execute_wmi_smb(device_data, commands_list, custom_credentials=custom_credentials)

    def get_files(self, device_data, files_path, custom_credentials=None):
        """
        gets a list of files.
        :param device_data: the device data.
        :param files_path: a list of paths, e.g. ["c:\\a.txt"]
        :return:
        """

        commands_list = []
        for fp in files_path:
            commands_list.append({"type": "getfile", "args": [fp]})

        return self.execute_wmi_smb(device_data, commands_list, custom_credentials=custom_credentials)

    def delete_files(self, device_data, files_path, custom_credentials=None):
        """
        deletes a list of files.
        :param device_data: the device data.
        :param files_path: a list of paths, e.g. ["c:\\a.txt"]
        :return:
        """

        commands_list = []
        for fp in files_path:
            commands_list.append({"type": "deletefile", "args": [fp]})

        return self.execute_wmi_smb(device_data, commands_list, custom_credentials=custom_credentials)

    def execute_binary(self, device_data, binary_file_path, binary_params, custom_credentials=None):
        """
        Executes a binary file. We do not get the contents of this file, but rather the absolute path
        of this file on the machine that runs the current execution code (not the target).

        Note! It is the requester's responsibility to delete this file from the running machine (the local one!
        the file is, ofcourse, being deleted from the target machine)
        :param device_data:the device data
        :param binary_buffer: the absolute path of the file, on this current machine.
        :param binary_params: a string to give as an argument to the binary.
                              we run eventually "cmd.exe /Q /c file.exe binary_params > ...."
        :return:
        """

        if os.path.isfile(binary_file_path) is False:
            raise ValueError(f"Error, file path {binary_file_path} is not a file (or does not exist)!")

        if type(binary_params) != str:
            raise ValueError(f"Error, type of binary_params should be string, but instead got {type(binary_params)}")

        return self.execute_wmi_smb(
            device_data,
            [{"type": "execbinary", "args": [binary_file_path, binary_params]}],
            custom_credentials=custom_credentials
        )

    def _execute_subprocess_generically(self, subprocess_arguments):
        """
        Generically executes a subprocess for execution needs
        :param subprocess_arguments: a list of strings to pass to subprocess
        :return: the stdout of this process
        """
        # Running the command.
        subprocess_handle = subprocess.Popen(subprocess_arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Checking if return code is zero, if not, it will raise an exception
        try:
            command_stdout, command_stderr = subprocess_handle.communicate(
                timeout=MAX_SUBPROCESS_TIMEOUT_FOR_EXEC_IN_SECONDS)
        except subprocess.TimeoutExpired:
            # The child process is not killed if the timeout expires, so in order to cleanup properly a well-behaved
            # application should kill the child process and finish communication (from python documentation)
            subprocess_handle.kill()
            command_stdout, command_stderr = subprocess_handle.communicate()
            err_log = "Execution Timeout after {0} seconds!! stdout: {1}, " \
                      "stderr: {2}, exception: {3}".format(MAX_SUBPROCESS_TIMEOUT_FOR_EXEC_IN_SECONDS,
                                                           str(command_stdout),
                                                           str(command_stderr),
                                                           get_exception_string(force_show_traceback=True))
            logger.warning(err_log)
            raise ValueError(err_log)
        except subprocess.SubprocessError:
            # This is a base class for all the rest of subprocess excpetions.
            err_log = f"General Execution error! command, exception: {get_exception_string(force_show_traceback=True)}"
            logger.warning(err_log, exc_info=True)
            raise ValueError(err_log)

        if subprocess_handle.returncode != 0:
            # Some efficiency
            if "Could not connect: [Errno 111] Connection refused" in command_stdout.decode("utf-8") \
                    or "Could not connect: [Errno 111] Connection refused" in command_stderr.decode("utf-8"):
                err_log = f"Error - Connection Refused!"
                logger.warning(err_log)
                raise ValueError(err_log)
            elif "Could not connect: [Errno 113] No route to host" in command_stdout.decode("utf-8") \
                    or "Could not connect: [Errno 113] No route to host" in command_stderr.decode("utf-8"):
                err_log = f"Error - No route to host!"
                logger.warning(err_log)
                raise ValueError(err_log)
            else:
                err_log = f"Execution Error! command returned returncode " \
                    f"{subprocess_handle.returncode}, stdout {command_stdout} stderr {command_stderr}"
                logger.warning(err_log)
                raise ValueError(err_log)

        return command_stdout.strip()

    def execute_axr(self, device_data, axr_commands, custom_credentials=None):
        """
        Executes commands through the AXR exe. This means that we send the axr exe and send the list of
        commands to it as a parameter.

        This also checks for hostname mismatch for all scenarios.
        :param device_data: the device data
        :param axr_commands: a list of objects, with commands that are in the exact format of execute_wmi_smb.
        :return:
        """

        if axr_commands is None or isinstance(axr_commands, list) and len(axr_commands) == 0:
            return {"result": 'Failure', "product": 'No WMI/SMB queries/commands list supplied'}

        # Build the axr
        commands = [{"type": "axr", "args": [axr_commands]}]

        # In some scenarios, we think we run code on device X while the dns is incorrect and it makes us
        # run code on device Y which has the same ip.
        # we see if the hostname we know this machine has is the same as what returned.

        command_list = self._get_basic_wmi_smb_command(
            device_data, custom_credentials=custom_credentials) + [json.dumps(commands)]
        logger.debug("running axr {0}".format(command_list))

        # Running the command.
        product = json.loads(self._execute_subprocess_generically(command_list))

        # Many validity check
        if len(product) != len(commands):
            err_log = f"Error, needed to run {commands} and expected the same length in return " \
                      f"but got {product}"
            logger.error(err_log)
            raise ValueError(err_log)

        if product[0]['status'].lower() != 'ok':
            err_log = f"Error, AXR did not return status ok, it is {product}"
            logger.error(err_log)
            raise ValueError(err_log)

        product = product[0]['data']  # we only had one wmi_smb_runner command

        if len(product['data']) != len(axr_commands):
            err_log = f"Error, needed to run {axr_commands} and expected the same length in return " \
                      f"but got {product}"
            logger.error(err_log)
            raise ValueError(err_log)

        # In some scenarios, we think we run code on device X while the dns is incorrect and it makes us
        # run code on device Y which has the same ip.
        # we see if the hostname we know this machine has is the same as what returned.
        try:
            if product.get('hostname'):
                hostname_on_device = product.get('hostname')
                hostname_on_ad = device_data['data']['hostname']
                if hostname_on_device is not None and hostname_on_device != "" and hostname_on_ad != "":
                    hostname_on_device = hostname_on_device.lower()
                    hostname_on_ad = hostname_on_ad.lower()
                    identity_tuple = (device_data["plugin_unique_name"], device_data["data"]["id"])
                    if not (hostname_on_device.startswith(hostname_on_ad) or
                            hostname_on_ad.startswith(hostname_on_device)):
                        logger.warning(f"Warning! hostname {hostname_on_ad} in our systems has an actual hostname "
                                       f"of {hostname_on_device}! Adding tags and failing")

                        self.devices.add_label([identity_tuple], "Hostname Conflict")
                        self.devices.add_data([identity_tuple], "Hostname Conflict",
                                              f"Hostname from Active Directory: '{hostname_on_ad}'\n'"
                                              f"Hostname on device: '{hostname_on_device}'")

                        return {
                            "result": 'Failure',
                            "product": f"Hostname Mismatch. Expected {hostname_on_ad} but got {hostname_on_device}"
                        }
                    else:
                        self.devices.add_label([identity_tuple], "Hostname Conflict", False)
                        self.devices.add_data([identity_tuple], "Hostname Conflict", False)
        except Exception:
            logger.exception("Exception in checking the hostname, continuing without check")

        # Optimization if all failed
        if all([True if line['status'] != 'ok' else False for line in product['data']]):
            return {"result": 'Failure', "product": product}

        # If we got here that means the the command executed successfuly
        return {"result": 'Success', "product": product['data']}

    def execute_wmi_smb(self, device_data, wmi_smb_commands, custom_credentials=None):
        """
        executes a list of wmi + smb possible queries. (look at wmi_smb_runner.py)
        :param device_data: the device data.
        :param wmi_smb_commands: a list of dicts, each list in the format of wmi_smb_runner.py.
                            e.g. [{"type": "query", "args": ["select * from Win32_Account"]}]
        :return: axonius-execution result.
        """

        if wmi_smb_commands is None:
            return {"result": 'Failure', "product": 'No WMI/SMB queries/commands list supplied'}

        hostname_validation = True
        for command in wmi_smb_commands:
            if command["type"].lower() in ["pm", "pmonline"]:
                # Due to a problem in impacket (look at wmi_smb_runner.py) we cannot query for wmi + rpc objects
                # in the same run. will be fixed in AX-1384
                hostname_validation = False

        # In some scenarios, we think we run code on device X while the dns is incorrect and it makes us
        # run code on device Y which has the same ip. That is why we append hostname query.
        # if the hostname returns, we see if the hostname we know this machine has is the same as what returned.
        if hostname_validation is True:
            wmi_smb_commands.append({"type": "query", "args": ["select Name from Win32_ComputerSystem"]})

        command_list = self._get_basic_wmi_smb_command(
            device_data, custom_credentials=custom_credentials) + [json.dumps(wmi_smb_commands)]
        logger.debug("running wmi {0}".format(command_list))

        # Running the command.
        product = json.loads(self._execute_subprocess_generically(command_list))

        # Some more validity check
        if len(product) != len(wmi_smb_commands):
            err_log = f"Error, needed to run {wmi_smb_commands} and expected the same length in return " \
                      f"but got {product}"
            logger.error(err_log)
            raise ValueError(err_log)

        # product[0] should have the hostname.
        if hostname_validation is True:
            hostname_answer = product.pop()
            try:
                if hostname_answer['status'] == 'ok':
                    hostname_on_device = hostname_answer["data"][0].get("Name")
                    hostname_on_ad = device_data['data']['hostname']
                    if hostname_on_device is not None and hostname_on_device != "" and hostname_on_ad != "":
                        hostname_on_device = hostname_on_device.lower()
                        hostname_on_ad = hostname_on_ad.lower()
                        identity_tuple = (device_data["plugin_unique_name"], device_data["data"]["id"])
                        if not (hostname_on_device.startswith(hostname_on_ad) or
                                hostname_on_ad.startswith(hostname_on_device)):
                            logger.warning(f"Warning! hostname {hostname_on_ad} in our systems has an actual hostname "
                                           f"of {hostname_on_device}! Adding tags and failing")

                            self.devices.add_label([identity_tuple], "Hostname Conflict")
                            self.devices.add_data([identity_tuple], "Hostname Conflict",
                                                  f"Hostname from Active Directory: '{hostname_on_ad}'\n'"
                                                  f"Hostname on device: '{hostname_on_device}'")

                            return {
                                "result": 'Failure',
                                "product": f"Hostname Mismatch. Expected {hostname_on_ad} but got {hostname_on_device}"
                            }
                        else:
                            self.devices.add_label([identity_tuple], "Hostname Conflict", False)
                            self.devices.add_data([identity_tuple], "Hostname Conflict", False)
            except Exception:
                logger.exception("Exception in checking the hostname, continuing without check")

        # Optimization if all failed
        if all([True if line['status'] != 'ok' else False for line in product]):
            return {"result": 'Failure', "product": product}

        # If we got here that means the the command executed successfuly
        return {"result": 'Success', "product": product}

    def execute_shell(self,
                      device_data,
                      shell_commands,
                      extra_files: Optional[dict] = None,
                      custom_credentials: Optional[dict] = None):
        """
        Shell commands is a dict of which keys are operation systems and values are lists of cmd commands.
        The commands will be run *in parallel* and not consequently.
        :param device_data: the device data
        :param shell_commands: e.g. {"Windows": ["dir", "ping google.com"]}
        :param extra_files: extra files to upload (a list of paths)
        :param custom_credentials: a dict of custom credentials to use, in format {'username': '', 'password': ''}
        :return:
        """

        shell_command_windows = shell_commands.get('Windows')
        if shell_command_windows is None:
            return {"result": 'Failure', "product": 'No Windows command supplied'}

        # Since wmi_smb_runner runs commands in parallel we first have to upload files then run commands.
        upload_files_commands_list = []
        for file_name, file_path in (extra_files or {}).items():
            file_name = file_name.split('/')[-1].split('\\')[-1]
            upload_files_commands_list.append({'type': 'putfilefromdisk', 'args': [file_path, file_name]})

        if upload_files_commands_list:
            res = self.execute_wmi_smb(device_data, upload_files_commands_list, custom_credentials=custom_credentials)
            if res.get('result') != 'Success':
                return res

        commands_list = [{"type": "shell", "args": [command]} for command in shell_command_windows]
        return self.execute_wmi_smb(device_data, commands_list, custom_credentials=custom_credentials)

    def supported_execution_features(self):
        """
        :return: Returns a list of all supported execution features by this adapter.
        """
        return ["put_files", "get_files", "delete_files", "execute_wmi_smb", "execute_shell", "execute_binary",
                "execute_axr"]

    def _enable_user(self, user_data, client_data_dict):
        client_data = self._resolve_client_from_client_dict_and_entity(client_data_dict, user_data)
        dn = user_data.get('ad_distinguished_name')
        assert dn, f"distinguishedName isn't in {user_data}"
        assert client_data.get_session("user_enabler").change_entity_enabled_state(dn, True), "Failed enabling user"

    def _disable_user(self, user_data, client_data_dict):
        client_data = self._resolve_client_from_client_dict_and_entity(client_data_dict, user_data)
        dn = user_data.get('ad_distinguished_name')
        assert dn, f"distinguishedName isn't in  {user_data}"
        assert client_data.get_session("user_disabler").change_entity_enabled_state(dn, False), "Failed disabling user"

    def _enable_device(self, device_data, client_data_dict):
        client_data = self._resolve_client_from_client_dict_and_entity(client_data_dict, device_data)
        dn = device_data.get('ad_distinguished_name')
        assert dn, f"distinguishedName isn't in  {device_data}"
        assert client_data.get_session("device_enabler").change_entity_enabled_state(dn, True), "Failed enabling device"

    def _disable_device(self, device_data, client_data_dict):
        client_data = self._resolve_client_from_client_dict_and_entity(client_data_dict, device_data)
        dn = device_data.get('ad_distinguished_name')
        assert dn, f"distinguishedName isn't in  {device_data}"
        assert client_data.get_session("device_disabler").change_entity_enabled_state(
            dn, False), "Failed disabling device"

    def change_ldap_attribute_data(self, entity_id, attribute_name, attribute_value, custom_creds=None):

        try:
            entity_finder = EntityFinder(self.devices_db, self._clients, self.plugin_unique_name)
            entity_data, client_data_dict = entity_finder.get_data_and_client_data(entity_id)
        except Exception:
            # maybe its a user. try that.
            entity_finder = EntityFinder(self.users_db, self._clients, self.plugin_unique_name)
            entity_data, client_data_dict = entity_finder.get_data_and_client_data(entity_id)
        try:
            if custom_creds and custom_creds.get('username') and custom_creds.get('password'):
                data = list(client_data_dict.values())
                if data:
                    data[0]['user'] = custom_creds.get('username')
                    data[0]['password'] = custom_creds.get('password')
        except Exception:
            logger.exception('Error setting custom credentials')
            return False

        client_data = self._resolve_client_from_client_dict_and_entity(client_data_dict, entity_data)

        with client_data:
            status = client_data.set_ldap_attribute(entity_id, attribute_name, attribute_value)

        return status

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            "items": [
                {
                    'name': 'resolving_enabled',
                    'title': 'Enable IP resolving',
                    'type': 'bool'
                },
                {
                    'name': 'dns_chunk_size',
                    'title': 'Max parallel DNS queries',
                    'type': 'number'
                },
                {
                    'name': 'verbose_auth_notifications',
                    'title': 'Show verbose notifications about connection failures',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_users_image',
                    'title': 'Fetch users image',
                    'type': 'bool'
                },
                {
                    'name': 'should_get_nested_groups_for_user',
                    'title': 'Get nested group membership for each user',
                    'type': 'bool'
                },
                {
                    'name': 'ldap_page_size',
                    'title': 'LDAP pagination (entries per page)',
                    'type': 'number'
                },
                {
                    'name': 'ldap_connection_timeout',
                    'title': 'LDAP socket connection timeout (seconds)',
                    'type': 'number'
                },
                {
                    'name': 'ldap_recieve_timeout',
                    'title': 'LDAP socket receive timeout (seconds)',
                    'type': 'number'
                },
                {
                    'name': LDAP_FIELD_TO_EXCLUDE_CONFIG,
                    'title': 'Devices to exclude by objectCategory',
                    'type': 'array',
                    'items': {
                        'type': 'string'
                    }
                },
                {
                    'name': 'ldap_sensitive_fields_to_exclude',
                    'title': 'LDAP fields to exclude',
                    'type': 'string'
                },
            ],
            "required": [
                'resolving_enabled',
                'fetch_users_image',
                'should_get_nested_groups_for_user',
                'ldap_page_size',
                'ldap_connection_timeout',
                'ldap_recieve_timeout',
                'verbose_auth_notifications'
            ],
            "pretty_name": "Active Directory Configuration",
            "type": "array"
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'resolving_enabled': True,
            'dns_chunk_size': 1000,
            'verbose_auth_notifications': False,
            'fetch_users_image': True,
            'should_get_nested_groups_for_user': True,
            'ldap_page_size': DEFAULT_LDAP_PAGE_SIZE,
            'ldap_connection_timeout': DEFAULT_LDAP_CONNECTION_TIMEOUT,
            'ldap_recieve_timeout': DEFAULT_LDAP_RECIEVE_TIMEOUT,
            'ldap_field_to_exclude': [],
            'ldap_sensitive_fields_to_exclude': ''
        }

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Manager, AdapterProperty.UserManagement]

    def outside_reason_to_live(self) -> bool:
        """
        This adapter might be called from outside, let it live
        """
        return True
