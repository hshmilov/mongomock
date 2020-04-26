import ipaddress
import logging

from axonius.adapter_base import AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.files import get_local_config_file
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.utils.datetime import parse_date
from panorays_adapter.connection import PanoraysConnection
from panorays_adapter.client_id import get_client_id
from panorays_adapter.consts import DEFAULT_PANORAYS_DOMAIN
from panorays_adapter.structures import PanoraysDeviceInstance, PanoraysFinding

logger = logging.getLogger(f'axonius.{__name__}')


class PanoraysAdapter(ScannerAdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(PanoraysDeviceInstance):
        pass

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
        connection = PanoraysConnection(domain=client_config['domain'],
                                        verify_ssl=client_config['verify_ssl'],
                                        https_proxy=client_config.get('https_proxy'),
                                        apikey=client_config['apikey'])
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
        The schema PanoraysAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Panorays Domain',
                    'type': 'string',
                    'default': DEFAULT_PANORAYS_DOMAIN
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
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_panorays_device_fields(device_raw: dict, device: MyDeviceAdapter, findings_raw):
        try:
            device.is_up = device_raw.get('is_up') if isinstance(device_raw.get('is_up'), bool) else None
            device.asset_type = device_raw.get('type')
            for finding_raw in findings_raw:
                try:
                    finding_data = PanoraysFinding(status=finding_raw.get('status'),
                                                   severity=finding_raw.get('severity'),
                                                   category=finding_raw.get('category'),
                                                   sub_category=finding_raw.get('sub_category'),
                                                   criterion_text=finding_raw.get('criterion_text'),
                                                   finding_text=finding_raw.get('finding_text'),
                                                   description=finding_raw.get('description'),
                                                   insert_time=parse_date(finding_raw.get('insert_ts')),
                                                   update_time=parse_date(finding_raw.get('update_ts')))
                    device.findings_data.append(finding_data)
                except Exception:
                    logger.exception(f'Problem with finding {finding_raw}')
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter, findings_dict):
        try:
            device_id = device_raw.get('name')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id
            try:
                ip = str(ipaddress.ip_address(device_id))
                device.add_nic(ips=[ip])
                device.add_public_ip(ip)
            except Exception:
                device.hostname = device_id
            device.first_seen = parse_date(device_raw.get('insert_ts'))
            findings_raw = findings_dict.get(device_id)
            if not findings_raw:
                findings_raw = []
            self._fill_panorays_device_fields(device_raw, device, findings_raw)

            device.set_raw(device_raw)

            return device
        except Exception:
            logger.exception(f'Problem with fetching Panorays Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """
        for device_raw, findings_dict in devices_raw_data:
            if not device_raw:
                continue
            try:
                # noinspection PyTypeChecker
                device = self._create_device(device_raw, self._new_device_adapter(), findings_dict)
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching Panorays Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
