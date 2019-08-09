import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.plugin_base import EntityType, add_rule, return_error
from axonius.fields import Field
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from carbonblack_defense_adapter.connection import CarbonblackDefenseConnection

logger = logging.getLogger(f'axonius.{__name__}')


class CarbonblackDefenseAdapter(AdapterBase, Configurable):
    # pylint: disable=R0902
    class MyDeviceAdapter(DeviceAdapter):
        av_status = Field(str, 'AV Status')
        policy_name = Field(str, 'Policy Name')
        email = Field(str, 'Email')
        basic_device_id = Field(str, 'Basic ID')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    @add_rule('change_policy', methods=['POST'])
    def change_policy(self):
        try:
            if self.get_method() != 'POST':
                return return_error('Method not supported', 405)
            cb_defense_dict = self.get_request_data_as_object()
            device_id = cb_defense_dict.get('device_id')
            client_id = cb_defense_dict.get('client_id')
            policy_name = cb_defense_dict.get('policy_name')
            cb_obj = self.get_connection(self._get_client_config_by_client_id(client_id))
            with cb_obj:
                device_raw = cb_obj.change_policy(device_id, policy_name)
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

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def get_connection(client_config):
        connection = CarbonblackDefenseConnection(domain=client_config['domain'],
                                                  verify_ssl=client_config['verify_ssl'],
                                                  https_proxy=client_config.get('https_proxy'),
                                                  apikey=client_config['apikey'],
                                                  connector_id=client_config['connector_id'])
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

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific CarbonblackDefense domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Carbonblack connection

        :return: A json with all the attributes returned from the Carbonblack Server
        """
        with client_data:
            yield from client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema CarbonblackDefenseAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Carbon Black CB Defense Domain',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'connector_id',
                    'title': 'Connector ID',
                    'type': 'string'
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
                'apikey',
                'connector_id',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('deviceId')
            if device_id is not None and device_id != '':
                device.id = str(device_id) + (device_raw.get('name') or '')
            else:
                logger.warning(f'Bad device ID {device_raw}')
                return None
            if self.__fetch_deregistred is False and device_raw.get('status') == 'DEREGISTERED':
                return None
            device.basic_device_id = device_id
            hostname = device_raw.get('name')
            if hostname and '\\' in hostname:
                split_hostname = hostname.split('\\')
                device.hostname = split_hostname[1]
                device.domain = split_hostname[0]
                device.part_of_domain = True
            else:
                device.hostname = hostname
            try:
                device.figure_os((device_raw.get('deviceType') or '') + ' ' + (device_raw.get('osVersion') or ''))
            except Exception:
                logger.exception(f'Problem adding os to :{device_raw}')
            try:
                macs = (device_raw.get('macAddress') or '').split(',')
                for mac in macs:
                    device.add_nic(mac, None)
            except Exception:
                logger.exception(f'Problem adding macs to {device_raw}')
            try:
                if device_raw.get('lastInternalIpAddress'):
                    device.add_nic(None, (device_raw.get('lastInternalIpAddress') or '').split(','))
            except Exception:
                logger.exception('Problem with adding nic to CarbonblackDefense device')
            try:
                device.last_seen = datetime.datetime.fromtimestamp(max((device_raw.get('lastReportedTime') or 0),
                                                                       (device_raw.get('lastContact') or 0)) / 1000)
            except Exception:
                logger.exception('Problem getting Last seen in CarbonBlackDefense')
            device.av_status = str(device_raw.get('avStatus'))
            device.email = device_raw.get('email')
            device.add_agent_version(agent=AGENT_NAMES.carbonblack_defense,
                                     version=device_raw.get('sensorVersion'),
                                     status=device_raw.get('status'))
            device.policy_name = device_raw.get('policyName')
            if device_raw.get('lastExternalIpAddress'):
                device.add_public_ip(device_raw.get('lastExternalIpAddress'))
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching CarbonblackDefense Device {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'fetch_deregistred',
                    'title': 'Fetch Deregistred Devices',
                    'type': 'bool'
                }
            ],
            'required': [
                'fetch_deregistred'
            ],
            'pretty_name': 'Carbonblack Defense Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'fetch_deregistred': True
        }

    def _on_config_update(self, config):
        self.__fetch_deregistred = config['fetch_deregistred']

    def outside_reason_to_live(self) -> bool:
        """
        This adapter might be called from outside, let it live
        """
        return True
