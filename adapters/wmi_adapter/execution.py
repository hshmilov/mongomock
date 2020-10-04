import copy
import ipaddress
import logging
import os
import shutil
import subprocess
from datetime import datetime
from multiprocessing.dummy import Pool
from typing import List, Tuple

from dataclasses import dataclass

from axonius.blacklists import DANGEROUS_IPS
from axonius.clients.wmi_query.consts import (ACTION_TYPES, CMD_ACTION_SCHEMA,
                                              COMMAND_NAME, DNS_SERVERS,
                                              EXTRA_FILES_NAME, HOSTNAMES,
                                              PARAMS_NAME, PASSWORD,
                                              SCAN_ACTION_SCHEMA, USERNAME, REGISTRY_EXISTS, USE_AD_CREDS)
from axonius.clients.wmi_query.query import WmiResults, WmiStatus
from axonius.clients.wmi_query.consts import WMI_SCAN_PORTS
from axonius.consts.plugin_consts import ACTIVE_DIRECTORY_PLUGIN_NAME, PLUGIN_UNIQUE_NAME
from axonius.devices.device_adapter import DeviceAdapter
from axonius.entities import EntityType
from axonius.fields import Field
from axonius.mixins.triggerable import RunIdentifier, Triggerable
from axonius.utils.db_querying_helper import iterate_axonius_entities
from axonius.utils.dns import async_query_dns_list
from axonius.utils.files import get_random_uploaded_path_name
from wmi_adapter.connection import WmiConnection

logger = logging.getLogger(f'axonius.{__name__}')

DNS_TIMEOUT = 5


@dataclass
class AdapterScanHostnames:
    """
    This class hosts network data about axonius adapter device
    """
    # adapter meta
    meta: dict
    # hostname
    hostname: str
    # ips list
    ips: List[str]


class WmiExecutionException(Exception):
    pass


class WmiExecutionMixIn(Triggerable):
    """
    This class should handle wmi scan/exec enforcement.
    """

    @staticmethod
    def _required_fields(job_name: str) -> str:
        """
        get required fields for each job
        :param job_name: job name for getting its required fields.
        :return: required fields schema
        """
        return {ACTION_TYPES.scan: SCAN_ACTION_SCHEMA['required'],
                ACTION_TYPES.cmd: CMD_ACTION_SCHEMA['required']}[job_name]

    @staticmethod
    def _pretty_job_name(job_name: str) -> str:
        """
        Get job pretty name
        :param job_name: job name
        :return: pretty job name
        """
        return {ACTION_TYPES.scan: 'Wmi Scan',
                ACTION_TYPES.cmd: 'Windows Shell Command'}[job_name]

    def _get_job_client_id(self, client_config: dict, job_name: str) -> str:
        """
        return a new client_id for each job using client_config
        :param client_config: client_config data
        :param job_name: job name
        :return: unique client_id
        """
        client_id = self._get_client_id(client_config)
        prefix = {ACTION_TYPES.scan: 'wmiscan',
                  ACTION_TYPES.cmd: 'cmd'}[job_name]
        return '_'.join([prefix, client_id])

    def _new_device(self, client_config: dict, job_name: str, hostname_for_validation: str) -> DeviceAdapter:
        """
        Return a new DeviceAdapter according to the given job.
        :param client_config: action config data
        :param job_name: requested job name
        :return: new device with data.
        """
        client_id = self._get_job_client_id(client_config, job_name)
        return {ACTION_TYPES.scan: self._run_scan,
                ACTION_TYPES.cmd: self._run_cmd}[job_name](client_config, client_id, hostname_for_validation)

    def get_valid_config(self, config: dict, job_name: str) -> dict:
        """
        Validate action config
        :param config: action config
        :param job_name: requested job name
        :return: config if all valid config fields exists, otherwise false.
        """
        try:
            required_fields = self._required_fields(job_name)
            if not all(arg in config for arg in required_fields):
                logger.error(f'Wrong action config: {config}')
                return None
            if not config.get(USERNAME) and not config.get(USE_AD_CREDS):
                logger.error('No username and not using ad creds')
                return None
        except Exception:
            logger.exception('Error when preparing arguments')
            return None
        return config

    def _handle_trigger(self, job_name: str, post_json: dict) -> dict:
        """
        handle action trigger command
        :param job_name: requested job
        :param post_json: action json data
        :return: action results
        """
        internal_axon_ids = post_json['internal_axon_ids']
        client_config = post_json['client_config']
        client_config = self.get_valid_config(client_config, job_name)
        if not client_config:
            logger.debug(f'Bad config {client_config}')
            return {
                'status': 'error',
                'message': f'Argument Error: Please specify valid Username and Password or use AD Creds'
            }

        devices = iterate_axonius_entities(EntityType.Devices, internal_axon_ids)
        with Pool(self._pool_size) as pool:
            args = ((device, client_config, job_name) for device in devices)
            results = dict(pool.starmap(self._handle_device, args))
        return results

    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args) -> dict:
        if job_name not in ACTION_TYPES:
            return super()._triggered(job_name, post_json, run_identifier, *args)

        job_title = self._pretty_job_name(job_name)
        logger.info(f'{job_title} was Triggered.')
        results = self._handle_trigger(job_name, post_json)
        logger.info(f'{job_title} Trigger end.')
        return results

    @staticmethod
    def _get_scan_hostnames(device: DeviceAdapter) -> List[AdapterScanHostnames]:
        """
        find all hostnames / ips to use for the device action
        :param device: device data
        :return: list of : (adapter_meta,adapter_hostname,[adapter ips]) for all adapters
        """
        result = []
        adapters = device.get('adapters')
        if not adapters:
            return result

        # Sort adapters data by the most recent one.
        adapters.sort(key=lambda i: i['accurate_for_datetime'], reverse=True)

        for adapter in adapters:
            try:
                adapter_ips = []
                adapter_data = adapter.get('data')
                if not adapter_data:
                    continue
                adapter_hostname = adapter_data.get('resolvable_hostname') or adapter_data.get('hostname')
                for interface in (adapter_data.get('network_interfaces', []) or []):
                    ips = interface.get('ips', [])
                    adapter_ips.extend(x for x in ips
                                       if isinstance(ipaddress.ip_address(x), ipaddress.IPv4Address) and
                                       not ipaddress.ip_address(x).is_loopback and x not in DANGEROUS_IPS)
                adapter_meta = adapter.copy()
                adapter_meta.pop('data')
                adapter_meta['adapter_unique_id'] = adapter.get('data', {}).get('id')
                result.append(AdapterScanHostnames(meta=adapter_meta, hostname=adapter_hostname, ips=adapter_ips))
            except Exception:
                logger.exception('Error getting network interfaces')

        return result

    @staticmethod
    def _is_windows_os(device: DeviceAdapter) -> bool:
        """
        Checks if the device os is Windows.
        if the device has no os return true because we can't know
        :param device: device for checking
        """
        os_list = []
        for adapter in (device.get('adapters', []) or []):
            try:
                os_name = adapter.get('data', {}).get('os', {}).get('type')
                if os_name:
                    os_list.append(os_name.upper())
            except Exception:
                logger.exception('Error getting adapter data')
        # if the device has no os return true because we can't know
        if not os_list:
            return True
        return 'WINDOWS' in os_list

    def handle_cmd_results(self, client_config: dict, client_id: str, output_data: WmiResults) -> DeviceAdapter:
        """
        :param client_config: dict of client config data
        :param client_id: client id
        :param output_data: a wmi exception or wmi exec output data
        :return:
        """
        # check if the output is an exception object
        if not output_data or isinstance(output_data, Exception):
            err_data = output_data if output_data else 'No output data'
            raise WmiExecutionException(f'Bad results from wmi execution: {err_data}')

        # get output data
        command_output = output_data[0].get('data')
        res_status = output_data[0].get('status')
        if res_status != WmiStatus.Success.value:
            raise WmiExecutionException(
                f'Bad results from wmi execution, status:{res_status}, output: {command_output}')

        field_name = client_config[COMMAND_NAME]
        field_name = field_name.strip().lower().replace(' ', '_').replace('-', '_')
        field_name_date = f'{field_name}_last_successful_wmi_execution'
        # create a new device for parsing he data
        new_device = self._new_device_adapter()
        new_device.id = f'{client_id}_{field_name}'
        if not new_device.does_field_exist(field_name):
            field = Field(str, f'Windows {field_name}')
            new_device.declare_new_field(field_name, field)
        if not new_device.does_field_exist(field_name_date):
            field = Field(datetime, f'Windows {field_name}: Last successful WMI execution')
            new_device.declare_new_field(field_name_date, field)
        new_device[field_name] = command_output
        new_device[field_name_date] = datetime.now()
        return new_device

    @staticmethod
    def local_delete_file(filename: str):
        """
        Delete a file from the filesystem
        :param filename: file to delete
        :return: None
        """
        try:
            if os.path.isfile(filename):
                os.unlink(filename)
        except Exception:
            logger.exception(f'Cannot delete {filename}')

    def _run_cmd(self, client_config: dict, client_id: str, hostname_for_validation) -> DeviceAdapter:
        """
        Run cmd command using wmi exec.
        :param client_config: action config data
        :param client_id: wmi client id
        :return: New device with command output as field
        """
        commands = client_config.get(PARAMS_NAME)
        connection = self.get_connection(client_config, hostname_for_validation)
        extra_files_raw = client_config.get(EXTRA_FILES_NAME, []) or []
        extra_files = {}
        # upload files to the device before running the command
        for file_raw in extra_files_raw:
            try:
                file_to_upload_from_db = self._grab_file(file_raw)
                random_filepath = get_random_uploaded_path_name('wmi_shell_extra_file')
                # Create a temp file on disk
                with open(random_filepath, 'wb') as binary_file:
                    # copy file data from db to the temp file
                    shutil.copyfileobj(file_to_upload_from_db, binary_file)
                extra_files[file_raw['filename']] = random_filepath
            except Exception:
                logger.exception(f'Error getting {file_raw}')

        # When "run cmd" is used only for deploying software there will be no commands.
        if commands:
            results = connection.exec_cmd([commands], extra_files=extra_files)
            # we have only one target.
            output_data = next(results)
            for filename, file_path in extra_files.items():
                os.remove(file_path)
            return self.handle_cmd_results(client_config, client_id, output_data)

        return None

    def get_creds_from_active_directory(self, node_id: str) -> Tuple[str, str]:
        """
        Get credentials from active directory adapter
        :param node_id: adapter node_id
        :return: username and password
        """
        # Get active directory credentials from active directory adapter
        active_directory_adapter_unique_name = self.get_plugin_by_name(
            ACTIVE_DIRECTORY_PLUGIN_NAME, node_id=node_id)[PLUGIN_UNIQUE_NAME]
        ad_client = self._get_db_connection()[active_directory_adapter_unique_name]['clients'].find_one()
        if ad_client:
            client_config = ad_client.get('client_config')
            # decrypt client config
            for key, val in client_config.items():
                if val:
                    client_config[key] = self.db_decrypt(val)
            return client_config.get('user'), client_config.get('password')
        return '', ''

    def get_connection(self, client_config: dict, hostname_for_validation: str) -> WmiConnection:
        """
        Return a new WmiConnection Instance from client config data
        :param client_config: client config data
        :param hostname_for_validation: hostname for hostname validation query
        :return: A new WmiConnection instance
        """
        node_id = client_config.get('instance')
        if client_config.get(USE_AD_CREDS):
            try:
                username, password = self.get_creds_from_active_directory(node_id)
            except Exception:
                logger.exception(f'Error getting credentials from Active Directory. node id: {node_id}')
                raise WmiExecutionException('Error getting credentials from Active Directory')
        else:
            username = client_config[USERNAME]
            password = client_config[PASSWORD]
        return WmiConnection(targets=client_config[HOSTNAMES],
                             username=username,
                             password=password,
                             dns_servers=client_config.get(DNS_SERVERS),
                             registry_keys=client_config.get(REGISTRY_EXISTS),
                             hostname_for_validation=hostname_for_validation,
                             python27_path=self._python_27_path,
                             wmi_smb_path=self._use_wmi_smb_path)

    def _run_scan(self, client_config: dict, client_id: str, hostname_for_validation: str) -> DeviceAdapter:
        """
        Run a new wmi scan using the given config
        :param client_config: client config data
        :param client_id: client if
        :param hostname_for_validation: hostname for hostname validation query
        :return:
        """
        connection = self.get_connection(client_config, hostname_for_validation)
        data = self._query_devices_by_client(client_id, connection)
        devices = list(self._parse_raw_data(data))
        if not devices:
            raise WmiExecutionException(f'No results from wmi scan')
        # we should only get one device
        return devices[0]

    @staticmethod
    def get_reachable_hostname(adapters_hostnames: List[AdapterScanHostnames], dns_servers=None) \
            -> Tuple[dict, str, str]:
        """
        Get the best reachable ip for the action
        :param adapters_hostnames:
        :param dns_servers: dns servers for resolving
        :return: adatper meta data, hostname, ip
        """
        for adapter_data in adapters_hostnames:
            try:
                # first, try to resolve the adapter hostname and add it as the first ip
                if adapter_data.hostname:
                    queries = [{
                        'hostname': adapter_data.hostname,
                        'nameservers': [x.strip() for x in dns_servers.split(',') if x] if dns_servers else []
                    }]
                    result = async_query_dns_list(queries, DNS_TIMEOUT)[0]

                    if result and result[0]:
                        resolved_hostname_ip, _ = result[0]
                        if resolved_hostname_ip:
                            adapter_data.ips.insert(0, resolved_hostname_ip)
            except Exception:
                logger.debug(f'Cannot resolve {adapter_data.hostname}')
            for ip in adapter_data.ips:
                try:
                    if WmiConnection.test_reachability(ip, dns_servers=dns_servers):
                        return adapter_data.meta, adapter_data.hostname, ip
                except Exception:
                    logger.exception(f'Error testing reachability for {ip}')

        return {}, '', ''

    def _handle_device(self, device, client_config, job_name):
        job_title = self._pretty_job_name(job_name)
        try:
            # Get the device adapter
            if not device.get('adapters'):
                json = {
                    'success': False,
                    'value': f'{job_title} Error: Adapters not found'
                }
                return device['internal_axon_id'], json

            # WMI is for windows only, so we validate that the device is a windows system
            if not self._is_windows_os(device):
                json = {
                    'success': False,
                    'value': f'{job_title} Error: Invalid Operating System'
                }
                return device['internal_axon_id'], json

            # Get the adapters hostnames data
            adapters_hostnames = self._get_scan_hostnames(device)
            if not adapters_hostnames or not \
                    any([adapter_hostname.hostname or adapter_hostname.ips for adapter_hostname in adapters_hostnames]):
                json = {
                    'success': False,
                    'value': f'{job_title} Error: Missing Hostname and IPs'
                }
                return device['internal_axon_id'], json

            # find the best ip for running the job on it
            reachable_hostname_adapter, reachable_hostname, reachable_ip = \
                self.get_reachable_hostname(adapters_hostnames, dns_servers=client_config.get(DNS_SERVERS) or None)

            job_config = copy.deepcopy(client_config)
            job_config[HOSTNAMES] = reachable_ip
            try:
                if adapters_hostnames[0]:
                    self._handle_device_create_device_general(job_config, adapters_hostnames[0].meta)
            except Exception:
                logger.exception(f'Could not run create device general')

            if not reachable_hostname and not reachable_ip:
                wmi_scan_ports_str = ', '.join([str(x) for x in WMI_SCAN_PORTS])
                json = {
                    'success': False,
                    'value': f'{job_title} Error: Unable to connect to ports {wmi_scan_ports_str}'
                }
                return device['internal_axon_id'], json

            # Running the given job
            self._handle_device_create_device(job_config, job_name, reachable_hostname_adapter, reachable_hostname)
            return device['internal_axon_id'], {
                'success': True,
                'value': f'{job_title} success'
            }
        except Exception as e:
            logger.exception('Exception while handling devices')
            return device['internal_axon_id'], {
                'success': False,
                'value': f'{job_title} Error: {str(e)}'
            }

    @staticmethod
    def does_answer_to_ping(hostnames) -> bool:
        try:
            hostnames = hostnames.split(',') if isinstance(hostnames, str) else hostnames
            for hostname in hostnames:
                res = subprocess.call(['ping', '-c', '1', hostname])
                if res == 0:
                    return True
        except Exception:
            logger.exception(f'Failed checking ping for {hostnames}')
        return False

    def set_last_ping_status(self, device, hostnames):
        try:
            if self.does_answer_to_ping(hostnames):
                device.wmi_adapter_does_answer_to_ping = True
                device.wmi_adapter_last_time_answered_to_ping = datetime.now()
            else:
                device.wmi_adapter_does_answer_to_ping = False
        except Exception:
            logger.exception(f'Could not set last ping fields')

    def _handle_device_create_device_general(self, client_config: dict, adapter_meta: dict):
        """
        Running the action job using the given details
        :param client_config: action config
        :param adapter_meta: adapter for tagging the new adapter data to it
        :return: None
        """
        # Create a new device
        new_device = self._new_device_adapter()
        self.set_last_ping_status(new_device, client_config[HOSTNAMES])

        new_data = new_device.to_dict()

        self.devices.add_adapterdata(
            [(adapter_meta['plugin_unique_name'], adapter_meta['adapter_unique_id'])], new_data,
            action_if_exists='update',  # If the tag exists, we update it using deep merge (and not replace it).
            client_used=adapter_meta['client_used']
        )

        logger.info(f'saved {new_data}')
        self._save_field_names_to_db(EntityType.Devices)

    def _handle_device_create_device(self, client_config: dict, job_name: str, adapter_meta: dict,
                                     hostname_for_validation: str):
        """
        Running the action job using the given details
        :param client_config: action config
        :param job_name: job to run
        :param adapter_meta: adapter for tagging the new adapter data to it
        :param hostname_for_validation: hostname for wmi query validation against the device
        :return: None
        """
        # Running the job and get the new device data
        new_device = self._new_device(client_config, job_name, hostname_for_validation)

        # When there is no commands for execution new_device will be None
        if not new_device:
            return
        # Save the new device to db_test_adapters_size
        new_device.wmi_adapter_last_success_execution = datetime.now()
        new_data = new_device.to_dict()

        if job_name == ACTION_TYPES.cmd:
            self.devices.add_data([(adapter_meta['plugin_unique_name'], adapter_meta['adapter_unique_id'])],
                                  new_device.id, new_data)
            # We don't want to replace the id
            new_data.pop('id')

        self.devices.add_adapterdata(
            [(adapter_meta['plugin_unique_name'], adapter_meta['adapter_unique_id'])], new_data,
            action_if_exists='update',  # If the tag exists, we update it using deep merge (and not replace it).
            client_used=adapter_meta['client_used']
        )
        self._save_field_names_to_db(EntityType.Devices)
