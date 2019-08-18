import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.plugin_base import EntityType, add_rule, return_error
from axonius.fields import Field
from cybereason_adapter.connection import CybereasonConnection
from cybereason_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class CybereasonAdapter(AdapterBase):
    # pylint: disable=R0902
    class MyDeviceAdapter(DeviceAdapter):
        agent_status = Field(str, 'Agent Status')
        agent_version = Field(str, 'Agent Version')
        site_name = Field(str, 'Site Name')
        ransomware_status = Field(str, 'Ransomware Status')
        isolated = Field(bool, 'Isolated')
        prevention_status = Field(str, 'Prevention Status')
        pylum_id = Field(str, 'Pylum ID')

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
        connection = CybereasonConnection(domain=client_config['domain'],
                                          verify_ssl=client_config['verify_ssl'],
                                          username=client_config['username'],
                                          password=client_config['password'],
                                          https_proxy=client_config.get('https_proxy'))
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            err_msg = str(e)
            if 'HTTP Status 403 - Forbidden' in str(e):
                err_msg = 'HTTP Status 403 - Forbidden'
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], err_msg)
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
        The schema CybereasonAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Cybereason Domain',
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

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            sensor_id = device_raw.get('sensorId')
            if not sensor_id:
                logger.warning(f'Bad device with no id {sensor_id}')
                return None
            try:
                mac_raw = sensor_id.split('_')[-1]
                if mac_raw and isinstance(mac_raw, str) and len(mac_raw) == 12:
                    device.add_nic(mac_raw, None)
            except Exception:
                logger.exception('Problem getting MAC address')
            device.pylum_id = device_raw.get('pylumId')
            device.id = sensor_id + '_' + (device_raw.get('machineName') or '')
            device.name = device_raw.get('machineName')
            device.hostname = device_raw.get('fqdn') or device_raw.get('machineName')
            if device_raw.get('externalIpAddress'):
                device.add_public_ip(device_raw.get('externalIpAddress'))
            if device_raw.get('internalIpAddress'):
                device.add_nic(None, [device_raw.get('internalIpAddress')])
            device.site_name = device_raw.get('siteName')
            device.ransomware_status = device_raw.get('ransomwareStatus')
            device.isolated = device_raw.get('isolated')
            agent_status = device_raw.get('status')
            device.agent_status = agent_status
            if agent_status == 'Online':
                device.last_seen = datetime.datetime.utcnow()
            elif isinstance(device_raw.get('disconnectionTime'), int):
                try:
                    device.last_seen = datetime.datetime.fromtimestamp(device_raw.get('disconnectionTime') / 1000)
                except Exception:
                    logger.exception(f'Problem adding last seen to {device_raw}')
            device.prevention_status = device_raw.get('preventionStatus')
            device.figure_os((device_raw.get('osType') or '') + ' ' + (device_raw.get('osVersionType') or ''))

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Cybereason Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Endpoint_Protection_Platform]

    @add_rule('isolate_device', methods=['POST'])
    def isolate_device(self):
        return self._parse_isolating_request(True)

    @add_rule('unisolate_device', methods=['POST'])
    def unisolate_device(self):
        return self._parse_isolating_request(False)

    def _parse_isolating_request(self, do_isolate):
        try:
            if self.get_method() != 'POST':
                return return_error('Method not supported', 405)
            cybereason_response_dict = self.get_request_data_as_object()
            pylum_id = cybereason_response_dict.get('pylum_id')
            client_id = cybereason_response_dict.get('client_id')
            cybereason_obj = self.get_connection(self._get_client_config_by_client_id(client_id))
            with cybereason_obj:
                device_raw = cybereason_obj.update_isolate_status(pylum_id, do_isolate)
            if not device_raw:
                return return_error('Problem isolating device', 400)
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
        return '', 200

    def outside_reason_to_live(self) -> bool:
        """
        This adapter might be called from outside, let it live
        """
        return True
