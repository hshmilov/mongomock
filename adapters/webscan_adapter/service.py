import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from webscan_adapter.connection import WebscanConnection
from webscan_adapter.client_id import get_client_id
from webscan_adapter.consts import DEFAULT_SSL_PORT
from webscan_adapter.execution import WebscanExecutionMixIn
from webscan_adapter.scanners.cert_scanner import Cert
from webscan_adapter.scanners.cmseek.cmseek_scanner import CMS
from webscan_adapter.scanners.server_scanner import Server, ServerScanner
from webscan_adapter.scanners.ssllabs.ssllabs_scanner import SSLLabs

logger = logging.getLogger(f'axonius.{__name__}')


class WebscanAdapter(WebscanExecutionMixIn, AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        url = Field(str, 'Url')
        cms = Field(CMS, 'CMS')
        server = Field(Server, 'Server')
        powered_by = Field(str, 'Powered By')
        cert = Field(Cert, 'SSL Certificate')
        ssllabs = Field(SSLLabs, 'SSL Labs Data')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(
            client_config.get('domain'), port=client_config.get('port'), ssl=True,
            https_proxy=client_config.get('https_proxy')) or \
            RESTConnection.test_reachability(client_config.get('domain'),
                                             port=client_config.get('port'), ssl=False)

    @staticmethod
    def get_connection(client_config, fetch_ssllabs=False):
        connection = WebscanConnection(client_config['domain'], port=client_config['port'],
                                       https_proxy=client_config.get('https_proxy'), fetch_ssllabs=fetch_ssllabs)
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config, self._fetch_ssllabs)
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
            return client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema WebscanAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Web Server Domain',
                    'type': 'string'
                },
                {
                    'name': 'port',
                    'title': 'Web Server Port',
                    'type': 'integer',
                    'default': DEFAULT_SSL_PORT
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'port'
            ],
            'type': 'array'
        }

    def _create_device(self, device_raw):
        try:
            if not device_raw:
                logger.error('No data for device')
                return None
            services, raw_data = device_raw
            if not raw_data or not services:
                logger.error('No data for device')
                return None

            # parse basic server info
            server_data = raw_data.get(ServerScanner.__name__)
            device = self._new_device_adapter()
            device_id = server_data.get('domain') or server_data.get('ip')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id

            for service in services:
                try:
                    service.parse(device)
                except Exception:
                    logger.exception(f'Error parsing {service.__class__.__name__}')

            device.last_seen = datetime.datetime.now()
            device.set_raw(raw_data)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Webscan Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        device = self._create_device(devices_raw_data)
        yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]

    @classmethod
    def _db_config_schema(cls) -> dict:
        items = [{
            'name': 'fetch_ssllabs',
            'title': 'Fetch Data from SSL Labs',
            'type': 'bool',
            'required': True,
            'default': False
        }]
        return {
            'items': items,
            'required': ['fetch_ssllabs'],
            'pretty_name': 'Web Server Information Configuration',
            'type': 'array',
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'fetch_ssllabs': False
        }

    def _on_config_update(self, config):
        self._fetch_ssllabs = config.get('fetch_ssllabs', False)
