import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.datetime import parse_date
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from logrhythm_adapter.connection import LogrhythmConnection
from logrhythm_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class LogrhythmAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        long_description = Field(str, 'Long Description')
        risk_level = Field(str, 'Risk Level')
        threat_level = Field(str, 'Threat Level')
        host_zone = Field(str, 'Host Zone')
        location = Field(str, 'Location')
        entity_name = Field(str, 'Entity Name')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def _connect_client(client_config):
        try:
            with LogrhythmConnection(domain=client_config['domain'],
                                     verify_ssl=client_config['verify_ssl'],
                                     apikey=client_config['apikey'],
                                     https_proxy=client_config.get('https_proxy')
                                     ) as connection:
                return connection
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
        The schema LogrhythmAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Logrhythm Domain',
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
                }
            ],
            'required': [
                'domain',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('id')
                if device_id is None:
                    logger.warning(f'Bad device with not ID {device_raw}')
                    continue
                device.id = str(device_id) + '_' + (device_raw.get('name') or '')
                device.hostname = device_raw.get('name')
                device.description = device_raw.get('shortDesc') or device_raw.get('longDesc')
                if device_raw.get('longDesc'):
                    device.long_description = device_raw.get('longDesc')
                device.risk_level = device_raw.get('riskLevel')
                device.threat_level = device_raw.get('threatLevel')
                device.host_zone = device_raw.get('hostZone')
                try:
                    device.location = (device_raw.get('location') or {}).get('name')
                except Exception:
                    logger.exception(f'Problem getting location for {device_raw}')
                try:
                    device.entity_name = (device_raw.get('entity') or {}).get('name')
                except Exception:
                    logger.exception(f'Problem getting entity name for {device_raw}')
                try:
                    device.updated_at = parse_date(device_raw.get('dateUpdated'))
                except Exception:
                    logger.exception(f'Problem getting updated at for {device_raw}')
                try:
                    device.figure_os((device_raw.get('os') or '') + ' ' + (device_raw.get('or') or 'osType')
                                     + ' ' + (device_raw.get('osVersion') or ''))
                except Exception:
                    logger.exception(f'Problem getting os for {device_raw}')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Logrhythm Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
