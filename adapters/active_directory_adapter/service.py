import logging
from typing import Tuple, List

from axonius.devices import ad_entity
from axonius.mixins.configurable import Configurable
from axonius.smart_json_class import SmartJsonClass

from axonius.mixins.devicedisabelable import Devicedisabelable
from axonius.mixins.userdisabelable import Userdisabelable

logger = logging.getLogger(f"axonius.{__name__}")
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from axonius.fields import Field, JsonStringFormat, ListField
from datetime import datetime, timedelta
import json
import os
import os.path
import tempfile
import threading
import time
import subprocess
import ipaddress

from collections import defaultdict
from flask import jsonify
from active_directory_adapter.ldap_connection import LdapConnection, SSLState, LDAP_ACCOUNTDISABLE, \
    LDAP_PASSWORD_NOT_REQUIRED, LDAP_DONT_EXPIRE_PASSWORD
from active_directory_adapter.exceptions import LdapException, IpResolveError, NoClientError
from axonius.adapter_exceptions import ClientConnectionException, TagDeviceError
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.consts.adapter_consts import DEVICES_DATA, DNS_RESOLVE_STATUS, IPS_FIELDNAME, NETWORK_INTERFACES_FIELDNAME
from axonius.devices.device_adapter import DeviceAdapter
from axonius.devices.dns_resolvable import DNSResolvableDevice
from axonius.devices.ad_entity import ADEntity
from axonius.devices.dns_resolvable import DNSResolveStatus
from axonius.utils.dns import query_dns
from axonius.plugin_base import add_rule
from axonius.utils.files import get_local_config_file
from axonius.users.user_adapter import UserAdapter
from axonius.utils.parsing import parse_date, bytes_image_to_base64, ad_integer8_to_timedelta, \
    is_date_real, get_exception_string, convert_ldap_searchpath_to_domain_name, format_ip, \
    get_organizational_units_from_dn, get_member_of_list_from_memberof, get_first_object_from_dn


TEMP_FILES_FOLDER = "/home/axonius/temp_dir/"

LDAP_DONT_EXPIRE_PASSWORD = 0x10000
LDAP_PASSWORD_NOT_REQUIRED = 0x0020

# Note! After this time the process will be terminated. We shouldn't ever terminate a process while it runs,
# In case its the execution we might leave some files on the target machine which is a bad idea.
# For exactly this reason we have another mechanism to reject execution promises on the execution-requester side.
# This value should be for times we are really really sure there is a problem.
MAX_SUBPROCESS_TIMEOUT_FOR_EXEC_IN_SECONDS = 60 * 60 * 5


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


class ActiveDirectoryAdapter(Userdisabelable, Devicedisabelable, AdapterBase, Configurable):
    DEFAULT_LAST_SEEN_THRESHOLD_HOURS = -1
    DEFAULT_LAST_FETCHED_THRESHOLD_HOURS = 48
    DEFAULT_USER_LAST_SEEN = 30 * 24

    class MyDeviceAdapter(DeviceAdapter, DNSResolvableDevice, ADEntity):
        ad_service_principal_name = ListField(str, "AD Service Principal Name")
        ad_printers = ListField(ADPrinter, "AD Attached Printers")
        ad_dfsr_shares = ListField(ADDfsrShare, "AD DFSR Shares")

    class MyUserAdapter(UserAdapter, ADEntity):
        ad_user_principal_name = Field(str, "AD User Principal Name")
        user_managed_objects = ListField(str, "AD User Managed Objects")

    def __init__(self):

        # Initialize the base plugin (will initialize http server)
        super().__init__(get_local_config_file(__file__))

        self._resolving_thread_lock = threading.RLock()

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
                                           trigger=IntervalTrigger(seconds=60 * 60 * 5),  # Every five hours
                                           next_run_time=datetime.now() + timedelta(hours=2),
                                           name='change_resolve_status_thread',
                                           id='change_resolve_status_thread',
                                           max_instances=1)

        # Thread for inserting reports. Start in 30 minutes to allow the system to initialize
        # and especially the clients themselves -> it might take a couple of seconds to connect.
        self._background_scheduler.add_job(func=self.generate_report,
                                           trigger=IntervalTrigger(minutes=self.__report_generation_interval),
                                           next_run_time=datetime.now() + timedelta(seconds=30),
                                           name='report_generation_thread',
                                           id='report_generation_thread',
                                           max_instances=1
                                           )

        self._background_scheduler.start()

        # create temp files dir
        os.makedirs(TEMP_FILES_FOLDER, exist_ok=True)
        # TODO: Weiss: Ask why not using tempfile to creage dir.

    @add_rule('generate_report_now', methods=['POST'], should_authenticate=False)
    def generate_report_now(self):
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
            },
                upsert=True)

            time_needed = datetime.now() - time_needed
            logger.info(f"Statistics end (took {time_needed}), modified {update_result.modified_count} document in db")
        except Exception:
            self._get_collection("report").delete({"name": "report"})
            logger.exception("Exception while generating report")

    def _on_config_update(self, config):
        logger.info(f"Loading AD config: {config}")
        self.__sync_resolving = config['sync_resolving']
        self.__report_generation_interval = config['report_generation_interval']

        # Change interval of report generation thread
        try:
            jobs = self._background_scheduler.get_jobs()
            report_generation_thread_job = next(job for job in jobs if job.name == 'report_generation_thread')
            report_generation_thread_job.reschedule(trigger=IntervalTrigger(minutes=self.__report_generation_interval))
        except AttributeError:
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

    @property
    def _ldap_page_size(self):
        return int(self.config['others']['ldap_page_size'])

    def _get_client_id(self, dc_details):
        return dc_details['dc_name']

    def _connect_client(self, dc_details):
        try:
            return LdapConnection(self._ldap_page_size,
                                  dc_details['dc_name'],
                                  dc_details['user'],
                                  dc_details['password'],
                                  dc_details.get('dns_server_address'),
                                  SSLState[dc_details.get('use_ssl', SSLState.Unencrypted.name)],
                                  self._grab_file_contents(dc_details.get('ca_file')),
                                  self._grab_file_contents(dc_details.get('cert_file')),
                                  self._grab_file_contents(dc_details.get('private_key')),
                                  dc_details.get('fetch_disabled_devices', False),
                                  dc_details.get('fetch_disabled_users', False)
                                  )
        except LdapException as e:
            message = "Error in ldap process for dc {0}. reason: {1}".format(
                dc_details["dc_name"], str(e))
            logger.exception(message)
        except KeyError as e:
            if "dc_name" in dc_details:
                message = "Key error for dc {0}. details: {1}".format(
                    dc_details["dc_name"], str(e))
            else:
                message = "Missing dc name for configuration line"
            logger.exception(message)
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
                    "title": "User",
                    "type": "string"
                },
                {
                    "name": "password",
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                },
                {
                    "name": "wmi_smb_user",
                    "title": "WMI/SMB User",
                    "type": "string"
                },
                {
                    "name": "wmi_smb_password",
                    "title": "WMI/SMB Password",
                    "type": "string",
                    "format": "password"
                },
                {
                    "name": "dns_server_address",
                    "title": "DNS Server Address",
                    "type": "string"
                },
                {
                    "name": "use_ssl",
                    "title": "Use SSL for connection",
                    "type": "string",
                    "enum": [SSLState.Unencrypted.name, SSLState.Verified.name, SSLState.Unverified.name],
                    "default": SSLState.Unverified.name,
                },
                {
                    "name": "ca_file",
                    "title": "CA File",
                    "description": "The binary contents of the ca_file",
                    "type": "file",
                },
                {
                    "name": "cert_file",
                    "title": "Certificate File",
                    "description": "The binary contents of the cert_file",
                    "type": "file",
                },
                {
                    "name": "private_key",
                    "title": "Private Key File",
                    "description": "The binary contents of the private_key",
                    "type": "file",
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
                }
            ],
            "required": [
                "dc_name",
                "user",
                "domain_name",
                "password"
            ],
            "type": "array"
        }

    def _query_devices_by_client(self, client_name, client_data: LdapConnection):
        """
        Get all devices from a specific Dc

        :param str client_name: The name of the client
        :param str client_data: The data of the client

        :return: iter(dict) with all the attributes returned from the DC per client
        """
        client_data.reconnect()
        return client_data.get_extended_devices_list()

    def _query_users_by_client(self, client_name, client_data):
        """
        Get a list of users from a specific DC.

        :param client_name: The name of the client
        :param client_data: The data of the client.
        :return:
        """

        return client_data.get_users_list()

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
        ad_entity.ad_is_critical_system_object = raw_data.get("isCriticalSystemObject")
        ad_entity.ad_member_of = get_member_of_list_from_memberof(raw_data.get("memberOf"))
        ad_entity.ad_managed_by = get_first_object_from_dn(raw_data.get('managedBy'))
        ad_entity.ad_msds_allowed_to_delegate_to = raw_data.get("msDS-AllowedToDelegateTo")
        ad_entity.figure_out_dial_in_policy(raw_data.get('msNPAllowDialin'))
        ad_entity.figure_out_delegation_policy(raw_data.get("userAccountControl"),
                                               raw_data.get("msDS-AllowedToDelegateTo"))

        # If pwdLastSet is 0 (which is, in date time, 1/1/1601) then it means the password must change now.
        # is_date_real checks if the date is a "special" date like 1/1/1601 and if it is - the date is not real,
        # which means its 0.
        ad_entity.ad_pwd_must_change = is_date_real(raw_data.get("pwdLastSet")) is False

        ad_entity.parse_user_account_control(raw_data.get("userAccountControl"))

    def _parse_users_raw_data(self, raw_data):
        """
        Gets raw data and yields User objects.
        :param user_raw_data: the raw data we get.
        :return:
        """

        for user_raw in raw_data:
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
                user.description = user_raw.get('description')
                user.domain = domain_name
                user.id = f"{username}@{domain_name}"  # Should be the unique identifier of that user.

                user.mail = user_raw.get("mail")
                user.ad_user_principal_name = user_raw.get("userPrincipalName")
                user.is_local = False
                is_admin = user_raw.get("adminCount")
                if is_admin is not None:
                    user.is_admin = bool(is_admin)

                use_timestamps = []  # Last usage times
                user.account_expires = parse_date(user_raw.get("accountExpires"))
                user.last_bad_logon = parse_date(user_raw.get("badPasswordTime"))
                pwd_last_set = parse_date(user_raw.get("pwdLastSet"))
                if is_date_real(pwd_last_set):
                    user.last_password_change = pwd_last_set
                    # parse maxPwdAge
                    max_pwd_age = user_raw.get("axonius_extended", {}).get("maxPwdAge")
                    if max_pwd_age is not None:
                        user.password_expiration_date = pwd_last_set + ad_integer8_to_timedelta(max_pwd_age)
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
                    user.password_never_expires = bool(user_account_control & LDAP_DONT_EXPIRE_PASSWORD)
                    user.password_not_required = bool(user_account_control & LDAP_PASSWORD_NOT_REQUIRED)
                    user.account_disabled = bool(user_account_control & LDAP_ACCOUNTDISABLE)

                # I'm afraid this could cause exceptions, lets put it in try/except.
                try:
                    thumbnail_photo = user_raw.get("thumbnailPhoto") or \
                        user_raw.get("exchangePhoto") or \
                        user_raw.get("jpegPhoto") or \
                        user_raw.get("photo") or \
                        user_raw.get("thumbnailLogo")
                    if thumbnail_photo is not None:
                        if type(thumbnail_photo) == list:
                            thumbnail_photo = thumbnail_photo[0]        # I think this can happen from some reason..
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

                user.set_raw(user_raw)
                yield user
            except Exception:
                logger.exception(f"Exception while parsing user {user_raw.get('distinguishedName')}, bypassing")

    def _resolve_hosts_addresses(self, hosts):
        for host in hosts:
            time_before_resolve = datetime.now()
            dns_name = host.get('AXON_DNS_ADDR')
            dc_name = host.get('AXON_DC_ADDR')
            current_resolved_host = dict(host)
            try:
                ips_and_dns_servers = self._resolve_device_name(host['hostname'],
                                                                {"dns_name": dns_name,
                                                                 "dc_name": dc_name})
                ips = [ip for ip, _ in ips_and_dns_servers]
                ips = list(set(ips))    # make it unique

                current_resolved_host[IPS_FIELDNAME] = ips
                current_resolved_host[DNS_RESOLVE_STATUS] = DNSResolveStatus.Resolved.name

            except Exception:
                # Don't log here, it will happen for every failed resolving (Can happen a lot of times)
                current_resolved_host = dict(host)
                current_resolved_host[IPS_FIELDNAME] = []
                current_resolved_host[DNS_RESOLVE_STATUS] = DNSResolveStatus.Failed.name
            else:
                try:
                    available_ips = {ip: dns for ip, dns in ips_and_dns_servers}
                    if len(available_ips) > 1:
                        # If we have more than one key in available_ips that means
                        # that this device got two different IP's
                        # i.e duplicate! we need to tag this device
                        logger.info(f"Found ip conflict. details: {str(available_ips)} on {host['id']}")
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

            finally:
                # yield first, so that if the handling takes more then the dns resolving time we won't wait it
                yield current_resolved_host
                resolve_time = (datetime.now() - time_before_resolve).microseconds / 1e6  # seconds
                time_to_sleep = max(0.0, 0.05 - resolve_time)
                time.sleep(time_to_sleep)

    def _resolve_hosts_addr_thread(self):
        """ Thread for ip resolving of devices.
        This thread will try to resolve IP's of known devices.
        """
        with self._resolving_thread_lock:
            hosts = self._get_collection(DEVICES_DATA).find({DNS_RESOLVE_STATUS: DNSResolveStatus.Pending.name},
                                                            projection={'_id': True,
                                                                        'id': True,
                                                                        'AXON_DNS_ADDR': True,
                                                                        'AXON_DC_ADDR': True,
                                                                        'hostname': True})

            logger.debug(f"Going to resolve for {hosts.count()} hosts")

            did_one_resolved = False

            for resolved_host in self._resolve_hosts_addresses(hosts):
                if resolved_host.get(IPS_FIELDNAME) is not None:
                    if resolved_host[DNS_RESOLVE_STATUS] == DNSResolveStatus.Resolved.name:
                        did_one_resolved = True
                    self._get_collection(DEVICES_DATA).update_one(
                        {"_id": resolved_host["_id"]},
                        {'$set':
                         {IPS_FIELDNAME: resolved_host[IPS_FIELDNAME],
                          DNS_RESOLVE_STATUS: resolved_host[DNS_RESOLVE_STATUS]}
                         }
                    )

            if not did_one_resolved and hosts.count() != 0:
                # Raise log message only if no host could get resolved
                logger.debug("Couldn't resolve IP's. Maybe dns is incorrect?")
            return

    def _resolve_change_status_thread(self):
        """ This thread is responsible for restarting the name resolving process
        """
        with self._resolving_thread_lock:
            hosts = self._get_collection(DEVICES_DATA).find({DNS_RESOLVE_STATUS: DNSResolveStatus.Pending.name},
                                                            limit=2)
            if hosts.count() == 0:
                self._get_collection(DEVICES_DATA).update_many({}, {'$set': {DNS_RESOLVE_STATUS:
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

    def _parse_raw_data(self, extended_devices_list):
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
        dns_resolved_devices_collection = self._get_collection(DEVICES_DATA)
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

        for device_raw in devices_raw_data:
            try:
                last_logon = device_raw.get('lastLogon')
                last_logon_timestamp = device_raw.get('lastLogonTimestamp')

                if last_logon is not None and last_logon_timestamp is not None:
                    last_seen = max(last_logon, last_logon_timestamp)
                else:
                    last_seen = last_logon or last_logon_timestamp

                if last_seen is None or is_date_real(last_seen) is False:
                    # No data on the last timestamp of the device. Not inserting this device.
                    # This can happen quite a lot so we don't print any message.
                    last_seen = None
                    no_timestamp_count += 1

                device = self._new_device_adapter()
                self._parse_generic_ad_raw_data(device, device_raw)
                device.hostname = device_raw.get('dNSHostName', device_raw.get('name', ''))
                device.description = device_raw.get('description')
                device.network_interfaces = []
                device.last_seen = last_seen
                device.dns_resolve_status = DNSResolveStatus.Pending
                device.id = device_raw['distinguishedName']
                device.domain = convert_ldap_searchpath_to_domain_name(device_raw['distinguishedName'])
                device.part_of_domain = True
                device.organizational_unit = get_organizational_units_from_dn(device.id)
                service_principal_name = device_raw.get("servicePrincipalName")   # only for devices
                if not isinstance(service_principal_name, list):
                    service_principal_name = [str(service_principal_name)]
                device.ad_service_principal_name = service_principal_name   # only for devices

                # OS. we must change device.os only after figure_os which initializes it
                device.figure_os(device_raw.get('operatingSystem', ''))
                device.os.build = device_raw.get('operatingSystemVersion')
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
                        "AXON_DNS_ADDR": device_raw['AXON_DNS_ADDR'],
                        "AXON_DC_ADDR": device_raw['AXON_DC_ADDR'],
                        "dns_resolve_status": device_as_dict['dns_resolve_status']
                    }

                    if self.__sync_resolving and not self._is_adapter_old_by_last_seen(device_as_dict):
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
        full_device_name = device_name

        err = f"Resolving {full_device_name} {client_config}"

        ips = []

        try:
            dns_server = None
            ips.append((query_dns(full_device_name, timeout, dns_server), 'default'))
        except Exception as e:
            err += f"failed to resolve from {dns_server} <{e}>; "

        try:
            dns_server = client_config["dns_name"]
            ips.append((query_dns(full_device_name, timeout, dns_server), dns_server))
        except Exception as e:
            err += f"failed to resolve from {dns_server} <{e}>; "

        try:
            dns_server = client_config["dc_name"]
            ips.append((query_dns(full_device_name, timeout, dns_server), dns_server))
        except Exception as e:
            err += f"failed to resolve from {dns_server} <{e}>; "
        if ips:
            return ips

        raise IpResolveError(err)

    def _get_basic_wmi_smb_command(self, device_data):
        """ Function for formatting the base wmiqery command.

        :param dict device_data: The device_data used to create this command
        :return string: The basic command
        """
        clients_config = self._get_clients_config()
        wanted_client = device_data['client_used']
        for client_config in clients_config:
            client_config = client_config['client_config']
            if client_config["dc_name"] == wanted_client:
                # If wmi/smb user was not supplied, use the default one.
                client_username = client_config.get("wmi_smb_user")
                if client_username is None or client_username == "":
                    client_username = client_config['user']

                # If wmi/smb password was not supplied, use the default one.
                client_password = client_config.get("wmi_smb_password")
                if client_password is None or client_password == "":
                    client_password = client_config['password']

                # We have found the correct client. Getting credentials
                if '\\' in client_username:
                    domain_name, user_name = client_username.split('\\')
                else:
                    # This is a legitimate flow. Do not try to build the domain name from the configurations.
                    domain_name, user_name = "", client_username

                wanted_hostname = device_data['data']['hostname']
                password = client_password
                try:
                    # We resolve ip only for devices who have been resolved before.
                    # We do this to reduce the time execution tasks take for devices that we are sure
                    # will not be resolved.
                    number_of_previously_resolved_ips = 0
                    for ip in device_data['data'].get(NETWORK_INTERFACES_FIELDNAME, []):
                        number_of_previously_resolved_ips += len(ip.get(IPS_FIELDNAME, []))

                    if number_of_previously_resolved_ips > 0:
                        # If a device has been resolved already, our theory is that the resolving time will be
                        # close to immediate. that is why we re-resolve it.
                        device_ip, _ = self._resolve_device_name(wanted_hostname, client_config)[0]
                    else:
                        raise IpResolveError(f"hostname {wanted_hostname} has never been resolved, not resolving")
                except Exception:
                    logger.exception(f"Exception - could not resolve ip for execution.")
                    raise

                # Putting the file using wmi_smb_path.
                return [self._python_27_path, self._use_wmi_smb_path, domain_name, user_name, password, device_ip,
                        "//./root/cimv2"]
        raise NoClientError()  # Couldn't find an appropriate client

    def put_files(self, device_data, files_path, files_content):
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

        return self.execute_wmi_smb(device_data, commands_list)

    def get_files(self, device_data, files_path):
        """
        gets a list of files.
        :param device_data: the device data.
        :param files_path: a list of paths, e.g. ["c:\\a.txt"]
        :return:
        """

        commands_list = []
        for fp in files_path:
            commands_list.append({"type": "getfile", "args": [fp]})

        return self.execute_wmi_smb(device_data, commands_list)

    def delete_files(self, device_data, files_path):
        """
        deletes a list of files.
        :param device_data: the device data.
        :param files_path: a list of paths, e.g. ["c:\\a.txt"]
        :return:
        """

        commands_list = []
        for fp in files_path:
            commands_list.append({"type": "deletefile", "args": [fp]})

        return self.execute_wmi_smb(device_data, commands_list)

    def execute_binary(self, device_data, binary_file_path, binary_params):
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

        return self.execute_wmi_smb(device_data, [{"type": "execbinary", "args": [binary_file_path, binary_params]}])

    def execute_wmi_smb(self, device_data, wmi_smb_commands):
        """
        executes a list of wmi + smb possible queries. (look at wmi_smb_runner.py)
        :param device_data: the device data.
        :param wmi_smb_commands: a list of dicts, each list in the format of wmi_smb_runner.py.
                            e.g. [{"type": "query", "args": ["select * from Win32_Account"]}]
        :return: axonius-execution result.
        """

        if wmi_smb_commands is None:
            return {"result": 'Failure', "product": 'No WMI/SMB queries/commands list supplied'}

        command_list = self._get_basic_wmi_smb_command(device_data) + [json.dumps(wmi_smb_commands)]
        logger.debug("running wmi {0}".format(command_list))

        # Running the command.
        subprocess_handle = subprocess.Popen(command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Checking if return code is zero, if not, it will raise an exception
        try:
            command_stdout, command_stderr = subprocess_handle.communicate(
                timeout=MAX_SUBPROCESS_TIMEOUT_FOR_EXEC_IN_SECONDS)
        except subprocess.TimeoutExpired:
            # The child process is not killed if the timeout expires, so in order to cleanup properly a well-behaved
            # application should kill the child process and finish communication (from python documentation)
            subprocess_handle.kill()
            command_stdout, command_stderr = subprocess_handle.communicate()
            err_log = "Execution Timeout after {4} seconds!! command {0}, stdout: {1}, " \
                      "stderr: {2}, exception: {3}".format(command_list,
                                                           str(command_stdout),
                                                           str(command_stderr),
                                                           get_exception_string(),
                                                           MAX_SUBPROCESS_TIMEOUT_FOR_EXEC_IN_SECONDS)
            logger.error(err_log)
            raise ValueError(err_log)
        except subprocess.SubprocessError:
            # This is a base class for all the rest of subprocess excpetions.
            err_log = f"General Execution error! command {wmi_smb_commands}, exception: {get_exception_string()}"
            logger.error(err_log)
            raise ValueError(err_log)

        if subprocess_handle.returncode != 0:
            err_log = f"Execution Error! command {wmi_smb_commands} returned returncode " \
                      f"{subprocess_handle.returncode}, stdout {command_stdout} stderr {command_stderr}"
            logger.error(err_log)
            raise ValueError(err_log)

        product = json.loads(command_stdout.strip())
        logger.debug("command returned with return code 0 (successfully).")

        # Optimization if all failed
        if all([True if line['status'] != 'ok' else False for line in product]):
            return {"result": 'Failure', "product": product}

        # Some more validity check
        if len(product) != len(wmi_smb_commands):
            err_log = f"Error, needed to run {wmi_smb_commands} and expected the same length in return " \
                      f"but got {product}, stdout {command_stdout} stderr {command_stderr}"
            logger.error(err_log)
            raise ValueError(err_log)

        # If we got here that means the the command executed successfuly
        return {"result": 'Success', "product": product}

    def execute_shell(self, device_data, shell_commands):
        """
        Shell commands is a dict of which keys are operation systems and values are lists of cmd commands.
        The commands will be run *in parallel* and not consequently.
        :param device_data: the device data
        :param shell_commands: e.g. {"Windows": ["dir", "ping google.com"]}
        :return:
        """

        shell_command_windows = shell_commands.get('Windows')
        if shell_command_windows is None:
            return {"result": 'Failure', "product": 'No Windows command supplied'}

        commands_list = []
        for command in shell_command_windows:
            commands_list.append({"type": "shell", "args": [command]})

        return self.execute_wmi_smb(device_data, commands_list)

    def supported_execution_features(self):
        """
        :return: Returns a list of all supported execution features by this adapter.
        """
        return ["put_files", "get_files", "delete_files", "execute_wmi_smb", "execute_shell", "execute_binary"]

    def _enable_user(self, user_data, client_data):
        dn = user_data['raw'].get('distinguishedName')
        assert dn, f"distinguishedName isn't in 'raw' for {user_data}"
        assert client_data.get_session("user_enabler").change_entity_enabled_state(dn, True), "Failed enabling user"

    def _disable_user(self, user_data, client_data):
        dn = user_data['raw'].get('distinguishedName')
        assert dn, f"distinguishedName isn't in 'raw' for {user_data}"
        assert client_data.get_session("user_disabler").change_entity_enabled_state(dn, False), "Failed disabling user"

    def _enable_device(self, device_data, client_data):
        dn = device_data['raw'].get('distinguishedName')
        assert client_data.get_session("device_enabler").change_entity_enabled_state(dn, True), "Failed enabling device"

    def _disable_device(self, device_data, client_data):
        dn = device_data['raw'].get('distinguishedName')
        assert client_data.get_session("device_disabler").change_entity_enabled_state(
            dn, False), "Failed disabling device"

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            "items": [
                {
                    "name": "sync_resolving",
                    "title": "Wait for DNS resolving",
                    "type": "bool"
                },
                {
                    "name": "report_generation_interval",
                    "title": "Report Generation Interval (Minutes)",
                    "type": "number",
                }
            ],
            "required": [
                "sync_resolving",
                "report_generation_interval"
            ],
            "pretty_name": "Active Directory Configuration",
            "type": "array"
        }

    @classmethod
    def _db_config_default(cls):
        return {
            "sync_resolving": False,
            "report_generation_interval": 30
        }

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Manager]
