import logging
import re
from datetime import datetime
from typing import Tuple

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.mixins.configurable import Configurable
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from icinga_adapter import consts
from icinga_adapter.client_id import get_client_id
from icinga_adapter.connection import IcingaConnection

logger = logging.getLogger(f'axonius.{__name__}')


class CommandResult(SmartJsonClass):
    active = Field(bool, 'Active')
    check_source = Field(str, 'Check Source')
    command = Field(str, 'Command')
    exec_start = Field(datetime, 'Execution Start')
    exec_end = Field(datetime, 'Execution End')
    exit_status = Field(int, 'Exit Status')
    output = Field(str, 'Output')


class IcingaAdapter(AdapterBase, Configurable):
    BAD_IPS = ['127.0.0.1', 'localhost']

    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        groups = ListField(str, 'Groups')
        http_response = Field(str, 'Http')
        logged_in_users = Field(str, 'Logged In Users')
        check_command = Field(str, 'Check Command')
        command_result = Field(CommandResult, 'Command Result')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)
        self.parsers = {'disk': IcingaAdapter.parse_disk,
                        'http': IcingaAdapter.parse_http,
                        'users': IcingaAdapter.parse_users}

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                port=client_config.get('port', consts.DEFAULT_API_PORT))

    @staticmethod
    def get_connection(client_config):
        connection = IcingaConnection(domain=client_config['domain'],
                                      verify_ssl=client_config.get('verify_ssl', False),
                                      https_proxy=client_config.get('https_proxy'),
                                      username=client_config['username'],
                                      password=client_config['password'],
                                      port=client_config.get('port', consts.DEFAULT_API_PORT))
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema IcingaAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Icinga Domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'port',
                    'title': 'API Port',
                    'default': consts.DEFAULT_API_PORT,
                    'type': 'integer'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def get_service_results(service_data: dict) -> Tuple[dict, str]:
        """
        Get results output from icinga data
        :param service_data: raw service response data from icinga
        :return: results data
        """
        service_results = service_data.get('last_check_result')
        if not service_results:
            return None, None
        output = service_results.get('output')
        if not output:
            return service_results, None
        return service_results, output

    @staticmethod
    def parse_disk(device: DeviceAdapter, service_data: dict) -> None:
        """
        Parse nagios 'disk' command
        :param device: device data
        :param service_data: icinga service output
        :return: None
        """
        free_space = None
        total_size = None
        service_results, output = IcingaAdapter.get_service_results(service_data)
        if not service_results or not output:
            logger.error('No disk results')
            return
        res = re.search(r'(\d*) MB', output)
        if res:
            free_space = int(res.group(1)) / 1024
        perf_data = service_results.get('performance_data')
        if perf_data and isinstance(perf_data, list):
            output = perf_data[0].split(';').pop()
            if output:
                total_size = int(output) / 1024

        device.add_hd(device=service_data.get('display_name'),
                      free_size=free_space, total_size=total_size)

    @staticmethod
    def parse_http(device: DeviceAdapter, service_data: dict) -> None:
        """
        Parse http get command
        :param device: device data
        :param service_data: icinga service output
        :return: None
        """
        service_results, output = IcingaAdapter.get_service_results(service_data)
        if not service_results or not output:
            logger.error('No http results')
            return
        device.http_response = output

    @staticmethod
    def parse_users(device: DeviceAdapter, service_data: dict) -> None:
        """
        Parse users command
        :param device: device data
        :param service_data: icinga service output
        :return: None
        """
        service_results, output = IcingaAdapter.get_service_results(service_data)
        if not service_results or not output:
            logger.error('No users results')
            return
        device.logged_in_users = output

    def parse_services(self, device: DeviceAdapter, device_raw: dict) -> None:
        """
        Parse icinga services responses
        :param device: device data
        :param device_raw: device_raw data
        :return: None
        """
        services = (device_raw.get('services').get('results') if device_raw.get('services') else []) or []
        for service in services:
            service_data = service.get('attrs')
            if not service_data:
                continue
            command = service_data.get('check_command')
            parser = self.parsers.get(command)
            if parser and service_data.get('last_check_result'):
                try:
                    parser(device, service_data)
                except Exception:
                    logger.exception(f'Cannot parse service {command}')

    def _create_device(self, device_raw: dict) -> DeviceAdapter:
        try:
            device = self._new_device_adapter()
            device_data = device_raw.get('attrs')
            if not device_data or not device_data.get('__name'):
                logger.warning(f'Bad device with no ID {device_raw}')
                return None

            device.id = device_data.get('__name')
            device.name = device_data.get('display_name')
            if isinstance(device_data.get('address'), str):
                addresses = list(set(device_data.get('address').split(',')) - set(self.BAD_IPS))
                if addresses:
                    device.add_nic(ips=addresses)
            device.groups = device_data.get('groups')
            dev_vars = device_data.get('vars')
            if dev_vars:
                device.figure_os(dev_vars.get('os'))
            try:
                device.last_seen = parse_date(int(device_data.get('last_state_up'))) \
                    if device_data.get('last_state_up') else None
            except Exception:
                logger.exception(f'Error getting device last seen, device id: {device.id}')
            try:
                self.parse_services(device, device_raw)
            except Exception:
                logger.exception(f'Error parsing device services, device id: {device.id}')
            try:
                command_res = device_data.get('last_check_result')
                if command_res:
                    device.command_result = CommandResult(active=command_res.get('active'),
                                                          check_source=command_res.get('check_source'),
                                                          command=' '.join(command_res.get('command'))
                                                          if command_res.get('command') else None,
                                                          exec_start=parse_date(int(command_res.get('execution_start')))
                                                          if command_res.get('execution_start') else None,
                                                          exec_end=parse_date(int(command_res.get('execution_end')))
                                                          if command_res.get('execution_end') else None,
                                                          exit_status=command_res.get('exit_status'),
                                                          output=command_res.get('output'))
            except Exception:
                logger.exception(f'Error getting device command result, device id: {device.id}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Icinga Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        # AUTOADAPTER - check if you need to add other properties'
        return [AdapterProperty.Assets]
