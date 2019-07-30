import logging
import re
from multiprocessing.dummy import Pool

from axonius.clients.linux_ssh.consts import (ACTION_TYPES, CMD_ACTION_SCHEMA,
                                              COMMAND, COMMAND_NAME, HOSTNAME,
                                              IS_SUDOER, PASSWORD, PORT,
                                              PRIVATE_KEY, SCAN_ACTION_SCHEMA,
                                              USERNAME)
from axonius.clients.linux_ssh.data import DynamicFieldCommand
from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from axonius.mixins.triggerable import RunIdentifier, Triggerable
from axonius.plugin_base import EntityType
from axonius.types.correlation import CorrelationReason, CorrelationResult
from axonius.utils.gui_helpers import find_entity_field
from linux_ssh_adapter.connection import LinuxSshConnection

logger = logging.getLogger(f'axonius.{__name__}')

INVALID_HOSTS = ['localhost', 'ubuntu']
IP_REGEX = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'


def get_entity_field_list(device_data, field):
    """" find_entity_field returns object when single
         field exist and list when multiple objects exist.
         it hard to work like this, so this wrapper always returns a list """

    result = find_entity_field(device_data, field)
    if result is None:
        return []
    if not isinstance(result, list):
        result = [result]
    return result


class LinuxSshExecutionMixIn(Triggerable):

    @staticmethod
    def _required_fields(job_name):
        return {ACTION_TYPES.scan: SCAN_ACTION_SCHEMA['required'],
                ACTION_TYPES.cmd: CMD_ACTION_SCHEMA['required']}[job_name]

    @staticmethod
    def _pretty_job_name(job_name):
        return {ACTION_TYPES.scan: 'Linux SSH Scan',
                ACTION_TYPES.cmd: 'Linux Command'}[job_name]

    def _get_job_client_id(self, client_config, job_name):
        client_id = self._get_client_id(client_config)
        prefix = {ACTION_TYPES.scan: 'sshscan',
                  ACTION_TYPES.cmd: 'cmd'}[job_name]
        return '_'.join([prefix, client_id])

    def _new_device(self, client_config, job_name):
        client_id = self._get_job_client_id(client_config, job_name)
        return {ACTION_TYPES.scan: self._run_scan,
                ACTION_TYPES.cmd: self._run_cmd}[job_name](client_config, client_id)

    def get_valid_config(self, config, job_name):
        try:
            required_fields = self._required_fields(job_name)
            config = self._prepare_client_config(config)
            if not all(arg in config for arg in required_fields):
                return None
        except Exception:
            logger.exception('Error when preparing arguments')
            return None
        return config

    def _handle_trigger(self, job_name: str, post_json: dict):
        internal_axon_ids = post_json['internal_axon_ids']
        client_config = post_json['client_config']
        client_config = self.get_valid_config(client_config, job_name)
        if not client_config:
            logger.debug(f'Bad config {client_config}')
            return {'status': 'error', 'message': f'Argument Error: Please specify valid Username and Key/Password'}

        devices = [list(result)[0] for result in [self.devices.get(internal_axon_id=id_) for id_ in internal_axon_ids]]
        with Pool(self._pool_size) as pool:
            args = ((device, client_config, job_name) for device in devices)
            results = dict(pool.starmap(self._handle_device, args))
        return results

    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args):
        if job_name not in ACTION_TYPES:
            return super()._triggered(job_name, post_json, run_identifier, *args)

        job_title = self._pretty_job_name(job_name)
        logger.info(f'{job_title} was Triggered.')
        results = self._handle_trigger(job_name, post_json)
        logger.info(f'{job_title} Trigger end.')
        return results

    @staticmethod
    def _get_scan_hostnames(device):
        """ find all hostnames / ips to use for the device scan """
        result = []

        hostnames = get_entity_field_list(device.data, 'specific_data.data.hostname')
        hostnames = list(filter(lambda name: name not in INVALID_HOSTS, hostnames))
        result += hostnames

        ips = get_entity_field_list(device.data, 'specific_data.data.network_interfaces.ips')
        ips = filter(lambda ip: re.match(IP_REGEX, ip), ips)
        ips = list(filter(lambda ip: ip != '127.0.0.1', ips))
        result += ips

        return result

    def _run_scan(self, client_config, client_id):
        """ do the actual ssh scan logic """
        connection = LinuxSshConnection(hostname=client_config[HOSTNAME],
                                        port=client_config[PORT],
                                        username=client_config[USERNAME],
                                        password=client_config[PASSWORD],
                                        key=client_config[PRIVATE_KEY],
                                        is_sudoer=client_config[IS_SUDOER],
                                        timeout=self._timeout)

        data = self._query_devices_by_client(client_id, connection)
        # SSH adapter only yield one device per config
        # so we take only the first item from the iterator.
        device = list(self._parse_raw_data(data))[0]
        return device

    def _run_cmd(self, client_config, client_id):
        """ run the actual command """
        # pylint: disable=protected-access
        command = DynamicFieldCommand(client_config[COMMAND_NAME], client_config[COMMAND])
        connection = LinuxSshConnection(hostname=client_config[HOSTNAME],
                                        port=client_config[PORT],
                                        username=client_config[USERNAME],
                                        password=client_config[PASSWORD],
                                        key=client_config[PRIVATE_KEY],
                                        is_sudoer=client_config[IS_SUDOER],
                                        timeout=self._timeout)
        with connection:
            command.shell_execute(connection._execute_ssh_cmdline, client_config[PASSWORD])
        command.parse()
        new_device = self._new_device_adapter()
        command.to_axonius(client_id, new_device)
        return new_device

    @staticmethod
    def _is_linux_os(device):
        """ Checks if the device os is linux.
            if the device has no os return true because we can't know """

        os = get_entity_field_list(device.data, 'specific_data.data.os.type')
        linux_os = True
        if os:
            linux_os = 'Linux' in os
        return linux_os

    # pylint: disable=too-many-return-statements
    def _handle_device(self, device, client_config, job_name):
        job_title = self._pretty_job_name(job_name)
        try:
            if not device.specific_data:
                json = {'success': False, 'value': f'{job_title} Error: Adapters not found'}
                return (device.internal_axon_id, json)

            if not self._is_linux_os(device):
                json = {'success': False, 'value': f'{job_title} Error: Invalid Operating System'}
                return (device.internal_axon_id, json)

            hostnames = self._get_scan_hostnames(device)
            if not hostnames:
                json = {'success': False, 'value': f'{job_title} Error: Missing Hostname and IPs'}
                return (device.internal_axon_id, json)

            for hostname in hostnames:
                if LinuxSshConnection.test_reachability(hostname, client_config[PORT]):
                    client_config[HOSTNAME] = hostname
                    break
            else:
                json = {'success': False, 'value': f'{job_title} Error: Unable to connect'}
                return (device.internal_axon_id, json)

            self._handle_device_create_device(device, client_config, job_name)
            return (device.internal_axon_id, {'success': True, 'value': f'{job_title} success'})
        except Exception as e:
            logger.exception('Exception while handling devices')
            return (device.internal_axon_id, {'success': False, 'value': f'{job_title} Error: {str(e)}'})

    def _handle_device_create_device(self, device, client_config, job_name):
        client_id = self._get_job_client_id(client_config, job_name)
        new_device = self._new_device(client_config, job_name)
        # Here we create a new device adapter tab out of cycle
        self._save_data_from_plugin(client_id,
                                    {'raw': [], 'parsed': [new_device.to_dict()]},
                                    EntityType.Devices,
                                    False)
        self._save_field_names_to_db(EntityType.Devices)
        self._correlate_scan_if_needed(client_id, device, new_device)

    def _correlate_scan_if_needed(self, client_id, device, new_device):
        try:
            id_ = get_entity_field_list(device.data, 'adapters_data.linux_ssh_adapter.id')
            id_ = ''.join(id_)
            # If sshscan is in the "old" device id so this devices are already correlated
            # no need to correlate again.
            if client_id in id_:
                return

            logger.debug('Correlating scan')
            first_plugin_unique_name = device.specific_data[0][PLUGIN_UNIQUE_NAME]
            first_device_adapter_id = device.specific_data[0]['data']['id']
            new_device_id = new_device.id
            new_device = new_device.to_dict()

            associated_adapters = [(first_plugin_unique_name, first_device_adapter_id),
                                   (self.plugin_unique_name, new_device_id)]

            correlation = CorrelationResult(associated_adapters=associated_adapters,
                                            data={'reason': 'Linux SSH Scan'},
                                            reason=CorrelationReason.LinuxSSHScan)

            self.link_adapters(EntityType.Devices, correlation)
        except Exception as e:
            logger.exception('Failed to correlate')
