import logging
from urllib.parse import urlparse

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.mixins.configurable import Configurable
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from venafi_adapter.connection import VenafiConnection
from venafi_adapter.client_id import get_client_id
from venafi_adapter.structures import VenafiCertificateInstance
from venafi_adapter.consts import DEFAULT_ASYNC_CHUNKS, URL_API_FORMAT

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class VenafiAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(VenafiCertificateInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _create_url(url_to_parse):
        if not url_to_parse:
            return url_to_parse
        parsed_url = urlparse(url_to_parse)
        scheme = parsed_url.scheme or 'https'
        domain = parsed_url.netloc or parsed_url.path

        url = URL_API_FORMAT.format(scheme, domain)
        return url

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        auth_domain = VenafiAdapter._create_url(client_config.get('auth_domain'))

        connection = VenafiConnection(domain=client_config['domain'],
                                      auth_domain=auth_domain,
                                      client_id=client_config['client_id'],
                                      verify_ssl=client_config['verify_ssl'],
                                      https_proxy=client_config.get('https_proxy'),
                                      username=client_config['username'],
                                      password=client_config['password'])
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

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list(
                async_chunks=self.__async_chunks
            )

    @staticmethod
    def _clients_schema():
        """
        The schema VenafiAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Server Host Name or IP Address',
                    'type': 'string'
                },
                {
                    'name': 'auth_domain',
                    'title': 'Authentication Host Name or IP Address',
                    'type': 'string'
                },
                {
                    'name': 'client_id',
                    'title': 'Application ID',
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
                'client_id',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_venafi_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.parent_dn = device_raw.get('ParentDN')
            device.schema_class = device_raw.get('SchemaClass')
            device.approver = device_raw.get('Approver')
            device.authority_dn = device_raw.get('CertificateAuthorityDN')
            device.contact = device_raw.get('Contact')
            device.management_type = device_raw.get('ManagementType')

            if isinstance(device_raw.get('CertificateDetails'), dict):
                certificate_details = device_raw.get('CertificateDetails')
                device.issuer = certificate_details.get('Issuer')
                device.subject = certificate_details.get('Subject')
                device.thump_print = certificate_details.get('Thumbprint')
                device.valid_from = parse_date(certificate_details.get('ValidFrom'))
                device.valid_to = parse_date(certificate_details.get('ValidTo'))

        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('ID') or device_raw.get('GUID')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('Name') or '')

            device.name = device_raw.get('Name')
            device.first_seen = parse_date(device_raw.get('CreatedOn'))
            device.hostname = device_raw.get('DN')
            device.description = device_raw.get('Description')
            device.device_managed_by = device_raw.get('ManagedBy')

            if isinstance(device_raw.get('CertificateDetails'), dict):
                device.device_serial = device_raw.get('CertificateDetails').get('Serial')

            self._fill_venafi_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Venafi Device for {device_raw}')
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
                logger.exception(f'Problem with fetching Venafi Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'async_chunks',
                    'type': 'integer',
                    'title': 'Async chunks in parallel'
                }
            ],
            'required': [
                'async_chunks'
            ],
            'pretty_name': 'Venafi Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'async_chunks': DEFAULT_ASYNC_CHUNKS
        }

    def _on_config_update(self, config):
        self.__async_chunks = config.get('async_chunks') or DEFAULT_ASYNC_CHUNKS
