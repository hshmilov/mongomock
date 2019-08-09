import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.fields import Field
from axonius.plugin_base import EntityType, add_rule, return_error
from axonius.utils.atomicint import AtomicInteger
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import is_domain_valid
from carbonblack_response_adapter.connection import \
    CarbonblackResponseConnection

logger = logging.getLogger(f'axonius.{__name__}')


class CarbonblackResponseAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        sensor_health_message = Field(str, 'Sensor Health Message')
        is_isolating = Field(bool, 'Is Isolating')
        network_isolation_enabled = Field(bool, 'Network Isolation Enabled')
        sensor_id = Field(str, 'Sensor Id')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

        # The amount of threads inside _parse_isolating_request
        self.__working = AtomicInteger()

    @staticmethod
    def _get_client_id(client_config):
        return client_config['domain']

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def get_connection(client_config):
        connection = CarbonblackResponseConnection(domain=client_config['domain'],
                                                   verify_ssl=client_config.get('verify_ssl', False),
                                                   username=client_config.get('username'),
                                                   password=client_config.get('password'),
                                                   apikey=client_config.get('apikey'),
                                                   headers={'Content-Type': 'application/json',
                                                            'Accept': 'application/json'},
                                                   url_base_prefix='api/',
                                                   https_proxy=client_config.get('https_proxy'))
        with connection:
            pass  # check that the connection credentials are valid

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
        Get all devices from a specific CarbonblackResponse domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a CarbonblackResponse connection

        :return: A json with all the attributes returned from the CarbonblackResponse Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema CarbonblackAdapterResponse expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Carbon Black CB Response Domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'Username',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'apikey',
                    'title': 'API Token',
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
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=R0912,too-many-statements
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if not device_id:
                logger.warning(f'Bad device id {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('computer_name') or '')
            device.sensor_id = device_id
            device.sensor_health_message = device_raw.get('sensor_health_message')
            device.add_agent_version(agent=AGENT_NAMES.carbonblack_response,
                                     version=device_raw.get('build_version_string'),
                                     status=device_raw.get('status'))
            hostname = device_raw.get('computer_dns_name') or device_raw.get('computer_name')
            if device_raw.get('computer_dns_name') and device_raw.get('computer_name'):
                try:
                    device_name = device_raw.get('computer_name')
                    device.name = device_name
                    host_no_spaces_list = device.name.replace(' ', '-').split('-')
                    host_no_spaces_list[0] = ''.join(char for char in host_no_spaces_list[0] if char.isalnum())
                    if len(host_no_spaces_list) > 1:
                        host_no_spaces_list[1] = ''.join(char for char in host_no_spaces_list[1] if char.isalnum())
                    hostname = '-'.join(host_no_spaces_list).split('.')[0]
                except Exception:
                    logger.exception(f'Problem with hostname logic for {device_raw}')
            if '.' in hostname:
                domain = '.'.join(hostname.split('.')[1:])
                if is_domain_valid(domain):
                    device.domain = domain
            device.hostname = hostname
            device.figure_os(device_raw.get('os_environment_display_string', ''))
            try:
                if device_raw.get('network_adapters'):
                    for nic in device_raw.get('network_adapters').split('|'):
                        if nic:
                            ip_address, mac_address = nic.split(',')
                            device.add_nic(mac_address, [ip_address])
            except Exception:
                logger.exception(f'Problem with adding nic to CarbonblackResponse device {device_raw}')
            try:
                device.last_seen = parse_date(str(device_raw.get('last_checkin_time', '')))
            except Exception:
                logger.exception('Problem getting Last seen in CarbonBlackResponse')
            try:
                device.is_isolating = device_raw.get('is_isolating') or False
                device.network_isolation_enabled = device_raw.get('network_isolation_enabled') or False
            except Exception:
                logger.exception(f'Problem parsing isolating {device_raw}')
                device.is_isolating = False

            free_size = device_raw.get('systemvolume_free_size')
            total_size = device_raw.get('systemvolume_total_size')
            try:
                if free_size:
                    free_size = int(free_size) / (1024 ** 3)  # bytes -> gb
                else:
                    free_size = None
                if total_size:
                    total_size = int(total_size) / (1024 ** 3)  # bytes -> gb
                else:
                    total_size = None

                if free_size or total_size:
                    device.add_hd(total_size=total_size, free_size=free_size)
            except Exception:
                logger.exception(f'Problem setting hd. freesize is {free_size} totalsize is {total_size}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching CarbonblackResponse Device  {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]

    @add_rule('isolate_device', methods=['POST'])
    def isolate_device(self):
        return self._parse_isolating_request(True)

    @add_rule('unisolate_device', methods=['POST'])
    def unisolate_device(self):
        return self._parse_isolating_request(False)

    def _parse_isolating_request(self, do_isolate):
        try:
            self.__working.inc()
            if self.get_method() != 'POST':
                return return_error('Method not supported', 405)
            cb_response_dict = self.get_request_data_as_object()
            device_id = cb_response_dict.get('device_id')
            client_id = cb_response_dict.get('client_id')
            cb_obj = self.get_connection(self._get_client_config_by_client_id(client_id))
            with cb_obj:
                device_raw = cb_obj.update_isolate_status(device_id, do_isolate)
            device = self._create_device(device_raw)
            if device:
                self._save_data_from_plugin(
                    client_id,
                    {'raw': [], 'parsed': [device.to_dict()]},
                    EntityType.Devices, False)
                self._save_field_names_to_db(EntityType.Devices)
        except Exception as e:
            logger.exception(f'Problem during isolating changes')
            return return_error(str(e), 500)
        finally:
            self.__working.dec()
        return '', 200

    def outside_reason_to_live(self) -> bool:
        """
        Whether or not anything is in isolate/unisolate device
        """
        return self.__working.value > 0
