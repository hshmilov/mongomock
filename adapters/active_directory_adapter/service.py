from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from base64 import standard_b64decode
from datetime import datetime, timedelta
import json
import os
import tempfile
import threading
import time
import subprocess

from active_directory_adapter.ldap_connection import LdapConnection
from active_directory_adapter.exceptions import LdapException, IpResolveError, NoClientError
from axonius.adapter_exceptions import ClientConnectionException
from axonius.adapter_base import AdapterBase
from axonius.background_scheduler import LoggedBackgroundScheduler
from axonius.consts.adapter_consts import DEVICES_DATA, DNS_RESOLVE_STATUS
from axonius.devices.device import NETWORK_INTERFACES_FIELD, IPS_FIELD, MAC_FIELD
from axonius.devices.ad_device import ADDevice
from axonius.devices.dns_resolvable import DNSResolveStatus
from axonius.dns_utils import query_dns
from axonius.plugin_base import add_rule
from axonius.utils.files import get_local_config_file
from axonius.parsing_utils import get_exception_string

TEMP_FILES_FOLDER = "/home/axonius/temp_dir/"

# TODO ofir: Change the return values protocol


class ActiveDirectoryAdapter(AdapterBase):

    class MyDevice(ADDevice):
        pass

    def __init__(self):

        # Initialize the base plugin (will initialize http server)
        super().__init__(get_local_config_file(__file__))

        self._resolving_thread_lock = threading.RLock()

        executors = {'default': ThreadPoolExecutor(2)}
        self._resolver_scheduler = LoggedBackgroundScheduler(self.logger, executors=executors)

        # Thread for resolving IP addresses of devices
        self._resolver_scheduler.add_job(func=self._resolve_hosts_addr_thread,
                                         trigger=IntervalTrigger(minutes=2),
                                         next_run_time=datetime.now(),
                                         name='resolve_host_thread',
                                         id='resolve_host_thread',
                                         max_instances=1)
        # Thread for resetting the resolving process
        self._resolver_scheduler.add_job(func=self._resolve_change_status_thread,
                                         trigger=IntervalTrigger(seconds=60 * 60 * 5),  # Every five hours
                                         next_run_time=datetime.now() + timedelta(hours=2),
                                         name='change_resolve_status_thread',
                                         id='change_resolve_status_thread',
                                         max_instances=1)

        self._resolver_scheduler.start()

        # create temp files dir
        os.makedirs(TEMP_FILES_FOLDER, exist_ok=True)
        # TODO: Weiss: Ask why not using tempfile to creage dir.

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
            return LdapConnection(self.logger,
                                  self._ldap_page_size,
                                  dc_details['dc_name'],
                                  dc_details['domain_name'],
                                  dc_details['user'],
                                  dc_details['password'],
                                  dc_details.get('dns_server_address'))
        except LdapException as e:
            message = "Error in ldap process for dc {0}. reason: {1}".format(
                dc_details["dc_name"], str(e))
            self.logger.exception(message)
        except KeyError as e:
            if "dc_name" in dc_details:
                message = "Key error for dc {0}. details: {1}".format(
                    dc_details["dc_name"], str(e))
            else:
                message = "Missing dc name for configuration line"
            self.logger.error(message)
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
                    "title": "DC Name",
                    "type": "string"
                },
                {
                    "name": "domain_name",
                    "title": "Domain Name",
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
                    "name": "dns_server_address",
                    "title": "DNS Server Address",
                    "type": "string"
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

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Dc

        :param str client_name: The name of the client
        :param str client_data: The data of the client

        :return: iter(dict) with all the attributes returned from the DC per client
        """
        return client_data.get_device_list()

    def _query_users_by_client(self, client_name, client_data):
        """
        Get a list of users from a specific DC.

        :param client_name: The name of the client
        :param client_data: The data of the client.
        :return:
        """

        users_list = list(client_data.get_users_list())
        # The format is a list of objects that look like {"sid": "S-1-5-...", "caption": "username@domain.name"}
        # we gotta transfer that to the specific format requested by AdapterBase.clients()
        users_list_in_specific_format = {}
        for user in users_list:
            users_list_in_specific_format[user['sid']] = {"raw": user}

        return users_list_in_specific_format

    def _resolve_hosts_addresses(self, hosts):
        resolved_hosts = []
        for host in hosts:
            time_before_resolve = datetime.now()
            dns_name = host['raw'].get('AXON_DNS_ADDR')
            dc_name = host['raw'].get('AXON_DC_ADDR')
            current_resolved_host = dict(host)
            try:
                ip = self._resolve_device_name(host['hostname'], {"dns_name": dns_name, "dc_name": dc_name})
                network_interfaces = [{MAC_FIELD: None, IPS_FIELD: [ip]}]
                current_resolved_host[NETWORK_INTERFACES_FIELD] = network_interfaces
                current_resolved_host[DNS_RESOLVE_STATUS] = DNSResolveStatus.Resolved.name

            except Exception as e:
                self.logger.exception(f"Error resolving host ip from dc.")
                current_resolved_host = dict(host)
                current_resolved_host[DNS_RESOLVE_STATUS] = DNSResolveStatus.Failed.name

            finally:
                resolved_hosts.append(current_resolved_host)
                resolve_time = (datetime.now() - time_before_resolve).microseconds / 1e6  # seconds
                time_to_sleep = max(0.0, 0.05 - resolve_time)
                time.sleep(time_to_sleep)

        return resolved_hosts

    def _resolve_hosts_addr_thread(self):
        """ Thread for ip resolving of devices.
        This thread will try to resolve IP's of known devices.
        """
        with self._resolving_thread_lock:
            hosts = self._get_collection(DEVICES_DATA).find({DNS_RESOLVE_STATUS: DNSResolveStatus.Pending.name},
                                                            projection={'_id': True,
                                                                        'raw.AXON_DNS_ADDR': True,
                                                                        'raw.AXON_DC_ADDR': True,
                                                                        'hostname': True})

            self.logger.info(f"Going to resolve for {hosts.count()} hosts")

            did_one_resolved = False

            for resolved_host in self._resolve_hosts_addresses(hosts):
                if resolved_host.get(NETWORK_INTERFACES_FIELD) is not None:
                    if resolved_host[DNS_RESOLVE_STATUS] == DNSResolveStatus.Resolved.name:
                        did_one_resolved = True
                    self._get_collection(DEVICES_DATA).update_one({"_id": resolved_host["_id"]},
                                                                  {'$set':
                                                                   {NETWORK_INTERFACES_FIELD:
                                                                    resolved_host[NETWORK_INTERFACES_FIELD],
                                                                    DNS_RESOLVE_STATUS:
                                                                    resolved_host[DNS_RESOLVE_STATUS]}})

            if not did_one_resolved and hosts.count() != 0:
                # Raise log message only if no host could get resolved
                self.logger.error("Couldn't resolve IP's. Maybe dns is incorrect?")
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
        jobs = self._resolver_scheduler.get_jobs()
        reset_job = next(job for job in jobs if job.name == 'change_resolve_status_thread')
        reset_job.modify(next_run_time=datetime.now())
        self._resolver_scheduler.wakeup()
        resolve_job = next(job for job in jobs if job.name == 'resolve_host_thread')
        resolve_job.modify(next_run_time=datetime.now())
        self._resolver_scheduler.wakeup()
        return ''

    def _parse_raw_data(self, devices_raw_data):
        devices_collection = self._get_collection(DEVICES_DATA)
        all_devices = devices_collection.find({}, projection={'_id': False, 'id': True,
                                                              NETWORK_INTERFACES_FIELD: True,
                                                              DNS_RESOLVE_STATUS: True})
        all_devices_ids = {device['id']: {NETWORK_INTERFACES_FIELD: device[NETWORK_INTERFACES_FIELD],
                                          DNS_RESOLVE_STATUS: device[DNS_RESOLVE_STATUS]}
                           for device in all_devices}
        to_insert = []
        no_timestamp_count = 0
        for device_raw in devices_raw_data:
            last_logon = device_raw.get('lastLogon')
            last_logon_timestamp = device_raw.get('lastLogonTimestamp')

            last_seen = max(last_logon, last_logon_timestamp) \
                if last_logon is not None and last_logon_timestamp is not None \
                else last_logon or last_logon_timestamp

            if last_seen is None:
                # No data on the last timestamp of the device. Not inserting this device.
                no_timestamp_count += 1
                continue
            if type(last_seen) != datetime:
                self.logger.error(f"Unrecognized date format for "
                                  f"{device_raw.get('dNSHostName', device_raw.get('name', ''))}. "
                                  f"Got type {type(last_seen)} instead of datetime")
                continue

            device = self._new_device()
            device.hostname = device_raw.get('dNSHostName', device_raw.get('name', ''))
            device.figure_os(device_raw.get('operatingSystem', ''))
            device.network_interfaces = []
            device.last_seen = last_seen
            device.dns_resolve_status = DNSResolveStatus.Pending
            device.id = device_raw['distinguishedName']
            device.add_organizational_units(device.id)
            device.set_raw(device_raw)

            device_interfaces = all_devices_ids.get(device_raw['distinguishedName'])
            if device_interfaces is not None:
                device.network_interfaces = device_interfaces[NETWORK_INTERFACES_FIELD]
                device.dns_resolve_status = DNSResolveStatus[device_interfaces[DNS_RESOLVE_STATUS]]
            else:
                device_as_dict = device.to_dict()
                resolved_device = self._resolve_hosts_addresses([device_as_dict])[0]
                if resolved_device[DNS_RESOLVE_STATUS] == DNSResolveStatus.Resolved.name:
                    device.network_interfaces = resolved_device[NETWORK_INTERFACES_FIELD]
                    device.dns_resolve_status = DNSResolveStatus[resolved_device[DNS_RESOLVE_STATUS]]
                if not self.is_old_device(device_as_dict):
                    # That means that the device is new (As determined in adapter_base code)
                    to_insert.append(device_as_dict)

            yield device

        if len(to_insert) > 0:
            devices_collection.insert_many(to_insert)
        if no_timestamp_count != 0:
            self.logger.warning(f"Got {no_timestamp_count} with no timestamp while parsing data")

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

    def _resolve_device_name(self, device_name, client_config, timeout=2):
        """ Resolve a device name address using dns servers.
        This function will first try to resolve IP using the machine network interface DNS servers.
        If the servers cant find an appropriate IP, The function will try to query the DC (assuming that it
        is also a DNS server).

        :param dict device_name: The name of the device to resolve
        :param dict client_config:  Client data. Must contain 'dc_name'
        :param int timeout: The timeout for the dns query process. Since we try twice the function ca block
                            up to 3*timeout seconds
        :return: The ip address of the device
        :raises exception.IpResolveError: In case of an error in the query process
        """
        # We are assuming that the dc is the DNS server
        full_device_name = device_name

        err = f"Resolving {full_device_name} {client_config}"
        try:
            dns_server = None
            return query_dns(full_device_name, timeout, dns_server)
        except Exception as e:
            err += f"failed to resolve from {dns_server} <{e}>; "

        try:
            dns_server = client_config["dns_name"]
            return query_dns(full_device_name, timeout, dns_server)
        except Exception as e:
            err += f"failed to resolve from {dns_server} <{e}>; "

        try:
            dns_server = client_config["dc_name"]
            return query_dns(full_device_name, timeout, dns_server)
        except Exception as e:
            err += f"failed to resolve from {dns_server} <{e}>; "

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
                # We have found the correct client. Getting credentials
                domain_name, user_name = client_config['user'].split('\\')
                password = client_config['password']
                try:
                    device_ip = self._resolve_device_name(
                        device_data['data']['hostname'], client_config)
                except Exception as e:
                    self.logger.error(f"Could not resolve ip for execution. reason: {str(e)}")
                    raise IpResolveError("Cant Resolve Ip")

                # Putting the file using wmi_smb_path.
                return [self._python_27_path, self._use_wmi_smb_path, domain_name, user_name, password, device_ip]
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

    def execute_binary(self, device_data, binary_buffer):
        raise NotImplementedError("Execute binary is not implemented")

    def execute_wmi_smb(self, device_data, wmi_smb_commands):
        """
        executes a list of wmi + smb possible queries. (look at wmi_smb_runner.py)
        :param device_data: the device data.
        :param wmi_smb_commands: a list of dicts, each list in the format of wmirunner.py.
                            e.g. [{"type": "query", "args": ["select * from Win32_Account"]}]
        :return: axonius-execution result.
        """

        if wmi_smb_commands is None:
            return {"result": 'Failure', "product": 'No WMI/SMB queries/commands list supplied'}

        single_command = self._get_basic_wmi_smb_command(device_data) + [json.dumps(wmi_smb_commands)]
        self.logger.debug("running wmi {0}".format(single_command))

        # Running the command
        command_result = subprocess.run(single_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Checking if return code is zero, if not, it will raise an exception
        try:
            command_result.check_returncode()
        except subprocess.CalledProcessError as e:
            raise ValueError("command: {0}, stdout: {1}, stderr: {2}, exception: {3}"
                             .format(single_command,
                                     str(command_result.stdout),
                                     str(command_result.stderr),
                                     str(e)))

        product = json.loads(command_result.stdout.strip())
        self.logger.debug("command returned with return code 0 (successfully).")

        # Optimization if all failed
        if all([True if line['status'] != 'ok' else False for line in product]):
            return {"result": 'Failure', "product": product}

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
        return ["put_files", "get_files", "delete_files", "execute_wmi_smb", "execute_shell"]

        # Exported API functions - None for now
