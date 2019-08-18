import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from kaspersky_sc_adapter.connection import KasperskyScConnection
from kaspersky_sc_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class KasperskyScAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        last_full_scan = Field(datetime.datetime, 'Last Full Scan')
        virus_count = Field(int, 'Virus Count')

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
        connection = KasperskyScConnection(domain=client_config['domain'],
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
        The schema KasperskyScAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Kaspersky Security Center Domain',
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
            device_id = (device_raw.get('value') or {}).get('KLHST_WKS_HOSTNAME')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + ((device_raw.get('value') or {}).get('KLHST_WKS_FQDN') or '')
            device_value = (device_raw.get('value') or {})
            device.hostname = device_value.get('KLHST_WKS_FQDN')
            device_details = device_raw.get('details')
            device.figure_os(device_details.get('KLHST_WKS_OS_NAME'))
            try:
                device.last_full_scan = parse_date(device_details.get('KLHST_WKS_LAST_FULLSCAN').get('value'))
            except Exception:
                logger.exception(f'Problem getting last full scan for {device_raw}')
            try:
                device.virus_count = int(device_details.get('KLHST_WKS_VIRUS_COUNT').get('value'))
            except Exception:
                logger.exception(f'Problem getting virus count for {device_raw}')
            try:
                apps_raw = device_raw.get('apps') or []
                for sw_name in apps_raw:
                    try:
                        sw_version = apps_raw[sw_name].get('version')
                        device.add_installed_software(name=sw_name,
                                                      version=sw_version)
                    except Exception:
                        logger.exception(f'Problem with sw {sw_name}')

            except Exception:
                logger.exception(f'Problem getting sw data for {device_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching KasperskySc Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Endpoint_Protection_Platform]
