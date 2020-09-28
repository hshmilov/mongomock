import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.clients.limacharlie.connection import LimacharlieConnection
from axonius.clients.limacharlie.consts import API_URL
from axonius.utils.datetime import parse_date
from axonius.plugin_base import add_rule, return_error, EntityType
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw
from limacharlie_adapter.client_id import get_client_id
from limacharlie_adapter.structures import LimacharlieDeviceInstance

logger = logging.getLogger(f'axonius.{__name__}')


class LimacharlieAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(LimacharlieDeviceInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @add_rule('isolate_device', methods=['POST'])
    def isolate_device(self):
        return self._parse_isolating_request(True)

    @add_rule('unisolate_device', methods=['POST'])
    def unisolate_device(self):
        return self._parse_isolating_request(False)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(API_URL,
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = LimacharlieConnection(domain=API_URL,
                                           verify_ssl=client_config.get('verify_ssl'),
                                           https_proxy=client_config.get('https_proxy'),
                                           proxy_username=client_config.get('proxy_username'),
                                           proxy_password=client_config.get('proxy_password'),
                                           apikey=client_config['apikey'],
                                           org_id=client_config['org_id'])
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config.get('domain'), str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema LimacharlieAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'org_id',
                    'title': 'Organization ID',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
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
                },
                {
                    'name': 'proxy_username',
                    'title': 'HTTPS Proxy User Name',
                    'type': 'string'
                },
                {
                    'name': 'proxy_password',
                    'title': 'HTTPS Proxy Password',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                'org_id',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_limacharlie_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            online_raw = device_raw.get('online')
            if isinstance(online_raw, dict):
                device.is_online = online_raw.get('is_online')
            info_raw = device_raw.get('info')
            if not isinstance(info_raw, dict):
                info_raw = {}
            try:
                device.external_ip = info_raw.get('ext_ip')
                device.external_ip_raw.append(info_raw.get('ext_ip'))
            except Exception:
                pass
            device.sid = info_raw.get('sid')
            device.should_isolate = parse_bool_from_raw(info_raw.get('should_isolate'))
            device.is_kernel_available = parse_bool_from_raw(info_raw.get('is_kernel_available'))
            device.is_isolated = parse_bool_from_raw(info_raw.get('is_isolated'))
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            info_raw = device_raw.get('info')
            if not isinstance(info_raw, dict):
                info_raw = {}
            device_id = info_raw.get('sid')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (info_raw.get('hostname') or '')
            device.hostname = info_raw.get('hostname')
            if info_raw.get('int_ip'):
                device.add_nic(ips=[info_raw.get('int_ip')])
            device.last_seen = parse_date(info_raw.get('alive'))
            device.first_seen = parse_date(info_raw.get('enroll'))
            self._fill_limacharlie_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Limacharlie Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """
        for device_raw in devices_raw_data:
            if not device_raw:
                continue
            try:
                # noinspection PyTypeChecker
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching Limacharlie Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Endpoint_Protection_Platform]

    def _parse_isolating_request(self, do_isolate):
        try:
            if self.get_method() != 'POST':
                return return_error('Method not supported', 405)
            limacharlie_obj_response_dict = self.get_request_data_as_object()
            sid = limacharlie_obj_response_dict.get('sid')
            client_id = limacharlie_obj_response_dict.get('client_id')
            limacharlie_obj = self.get_connection(self._get_client_config_by_client_id(client_id))
            with limacharlie_obj:
                device_raw = limacharlie_obj.update_isolate_status(sid, do_isolate)
            if not device_raw:
                return return_error('Problem isolating device', 400)
            device = self._create_device(device_raw, self._new_device_adapter())
            if device:
                self._save_data_from_plugin(
                    client_id,
                    {'raw': [], 'parsed': [device.to_dict()]},
                    EntityType.Devices, False)
                self._save_field_names_to_db(EntityType.Devices)
        except Exception as e:
            logger.exception(f'Problem during isolating changes')
            return return_error(str(e), non_prod_error=True, http_status=500)
        return '', 200
