import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.fields import Field, ListField
from axonius.utils.datetime import parse_date
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from imperva_dam_adapter.connection import ImpervaDamConnection
from imperva_dam_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class ImpervaDamAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        agent_tags = ListField(str, 'Agent Tags')
        general_status = Field(str, 'General Status')
        start_time = Field(datetime.datetime, 'Start Time')
        last_status_update = Field(datetime.datetime, 'Last Status Update')
        throughput_kb = Field(int, 'Throughput Kb')
        connections_per_sec = Field(int, 'Connections Per Second')
        hits_per_sec = Field(int, 'Hits Per Second')
        cpu_utilization = Field(int, 'CPU Utilization')
        agent_version = Field(str, 'Agent Version')
        kernel_patch = Field(str, 'Kernel Patch')
        creation_time = Field(datetime.datetime, 'Creation Time')
        manual_settings_activation = Field(str, 'Manual Settings Activation')
        discovery_enabled = Field(bool, 'Discovery Enabled')
        discovery_scan_interval = Field(int, 'Discovery Scan Interval')
        agent_quota = Field(int, 'Agent Quota')
        logger_level = Field(str, 'Logger Level')
        cpu_usage_restraining = Field(bool, 'CPU Usage Restraining Enabled')
        cpu_usage_limit = Field(int, 'CPU Usage Limit')
        cpu_time_to_reactivate = Field(int, 'CPU Time To Reactivate')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def get_connection(client_config):
        connection = ImpervaDamConnection(domain=client_config['domain'],
                                          verify_ssl=client_config['verify_ssl'],
                                          https_proxy=client_config.get('https_proxy'),
                                          username=client_config['username'],
                                          password=client_config['password'])
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
        The schema ImpervaDamAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Imperva DAM Domain',
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

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('name')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id)
            device.name = device_raw.get('name')
            ip = device_raw.get('ip')
            device.add_nic(ips=[ip])
            try:
                device_details = device_raw.get('general_details')
                if not isinstance(device_details, dict):
                    device_details = {}
                device_status = device_details.get('status')
                if not isinstance(device_status, dict):
                    device_status = {}
                device.general_status = device_status.get('general-status')
                device.start_time = parse_date(device_status.get('start-time'))
                device.last_status_update = parse_date(device_status.get('last-status-update'))
                device.last_seen = parse_date(device_status.get('last-activity'))
                try:
                    device.connections_per_sec = int(device_status.get('connections-per-sec'))
                except Exception:
                    pass
                try:
                    device.throughput_kb = int(device_status.get('throughput-kb'))
                except Exception:
                    pass
                try:
                    device.hits_per_sec = int(device_status.get('hits-per-sec'))
                except Exception:
                    pass
                try:
                    device.cpu_utilization = int(device_status.get('cpu-utilization'))
                except Exception:
                    pass
                device_properties = device_details.get('properties')
                if not isinstance(device_properties, dict):
                    device_properties = {}
                device.agent_version = device_properties.get('Agent Version')
                device.kernel_patch = device_properties.get('Kernel Patch')
                device.figure_os(device_properties.get('Operating System'))
                device.hostname = device_properties.get('Hostname')
                device_info = device_details.get('general-info')
                if not isinstance(device_info, dict):
                    device_info = {}
                device.creation_time = parse_date(device_info.get('creation-time'))
                device.manual_settings_activation = device_info.get('manual-settings-activation')

            except Exception:
                logger.exception(f'Problem getting details for {device_raw}')
            if isinstance(device_raw.get('agent_tags'), list):
                device.agent_tags = device_raw.get('agent_tags')
            try:
                if isinstance(device_raw.get('open_ports'), list):
                    for open_port in device_raw.get('open_ports'):
                        if isinstance(open_port, dict):
                            port_id = None
                            if open_port.get('port'):
                                port_id = open_port.get('port')
                            device.add_open_port(port_id=port_id,
                                                 service_name=open_port.get('type'))
            except Exception:
                logger.exception(f'Problem with ports for {device_raw}')
            device_discovery = device_raw.get('discovery_settings')
            if isinstance(device_discovery, dict):
                device.discovery_enabled = bool(device_discovery.get('enabled'))
                try:
                    device.discovery_scan_interval = int(device_discovery.get('scan-interval'))
                except Exception:
                    pass
            try:
                device_config = device_raw.get('advanced_config')
                if isinstance(device_config, dict):
                    try:
                        device.agent_quota = int(device_config.get('quota'))
                    except Exception:
                        pass
                    device.logger_level = device_config.get('logger-level')
            except Exception:
                logger.exception(f'Problem with config {device_raw}')
            try:
                device_cpu = device_raw.get('cpu_usage')
                if isinstance(device_cpu, dict):
                    try:
                        device.cpu_time_to_reactivate = int(device_cpu.get('time-to-reactivate'))
                    except Exception:
                        pass
                    try:
                        device.cpu_usage_limit = int(device_cpu.get('cpu-usage-limit'))
                    except Exception:
                        pass
                    device.cpu_usage_restraining = bool(device_cpu.get('enabled'))
            except Exception:
                logger.exception(f'Problem with cpu for {device_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching ImpervaDam Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
