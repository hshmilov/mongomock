import logging
from datetime import timedelta

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from ip_fabric_adapter.connection import IpFabricConnection
from ip_fabric_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class IpFabricAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        boot_config_register = Field(str, 'Configuration Register')
        device_type = Field(str, 'Device Type')
        device_family = Field(str, 'Device Family')
        device_image = Field(str, 'Device Image')
        device_processor = Field(str, 'Device Processor')
        reload_reason = Field(str, 'Reload Reason')
        task_key = Field(str, 'Task Key')
        site_key = Field(str, 'Site Key')
        site_name = Field(str, 'Site Name')
        switching_domain = Field(str, 'Switching Domain')
        routing_domain = Field(str, 'Routing Domain')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = IpFabricConnection(domain=client_config['domain'],
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
        The schema IpFabricAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'IP Fabric Domain',
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

    @staticmethod
    def _fill_generic_fields(device, device_raw):
        try:
            device.figure_os(' '.join(map(lambda s: device_raw.get(s) or '',
                                          ['vendor', 'platform', 'family', 'version', 'processor'])))
            try:
                # Note: uptime might be "2 weeks, 6 days..."
                device.set_boot_time(uptime=timedelta(seconds=int(device_raw.get('uptime'))))
            except Exception:
                logger.exception(f'failed to parse uptime for device {device_raw}')

            device.hostname = device_raw.get('hostname')
            device.add_ips_and_macs(macs=[device_raw.get('mac')], ips=[device_raw.get('loginIp')])
            try:
                if isinstance(device_raw.get('uptime'), str):
                    # Note: uptime might be "2 weeks, 6 days..."
                    device.set_boot_time(uptime=timedelta(seconds=int(device_raw.get('uptime'))))
            except Exception:
                logger.exception(f'failed to parse uptime for device {device_raw}')

            try:
                if isinstance(device_raw.get('memoryTotalBytes'), str):
                    total_memory = float(device_raw.get('memoryTotalBytes')) / (1024 ** 3)  # bytes -> gb
                    device.total_physical_memory = total_memory
                    if isinstance(device_raw.get('memoryUsedBytes'), str):
                        used_gb = float(device_raw.get('memoryUsedBytes')) / (1024 ** 3)
                        device.free_physical_memory = total_memory - used_gb
                if isinstance(device_raw.get('memoryUtilization'), (str, float)):
                    device.physical_memory_percentage = float(device_raw.get('memoryUtilization'))
            except Exception:
                logger.exception(f'failed to parse total/free/precentage of physical memory for device {device_raw}')
            device.device_serial = device_raw.get('sn')
            device.add_open_port(service_name=device_raw.get('loginType'))
        except Exception:
            logger.exception(f'Failed filling generic fields for device {device_raw}')

    @staticmethod
    def _fill_specific_fields(device, device_raw):
        try:
            device.boot_config_register = device_raw.get('configReg')
            device.device_type = device_raw.get('devType')
            device.device_family = device_raw.get('family')
            device.device_image = device_raw.get('image')
            device.device_processor = device_raw.get('processor')
            device.reload_reason = device_raw.get('reload')
            device.task_key = device_raw.get('taskKey')
            device.site_key = device_raw.get('siteKey')
            device.site_name = device_raw.get('siteName')
            device.switching_domain = device_raw.get('stpDomain')
            device.routing_domain = device_raw.get('rd')
        except Exception:
            logger.exception(f'Failed filling generic fields for device {device_raw}')

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('hostname')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('mac') or '')
            self._fill_generic_fields(device, device_raw)
            self._fill_specific_fields(device, device_raw)
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching IpFabric Device for {device_raw}')
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
