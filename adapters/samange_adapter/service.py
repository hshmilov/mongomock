import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.fields import Field
from samange_adapter.connection import SamangeConnection
from samange_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class SamangeAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        owner = Field(str, 'Owner')
        updated_at = Field(datetime.datetime, 'Updated At')
        department = Field(str, 'Department')

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
            with SamangeConnection(domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
                                   apikey=client_config['apikey'],
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
        The schema SamangeAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Samange Domain',
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
                }
            ],
            'required': [
                'domain',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=R0912,R1702,R0915
    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('id')
                if device_id is None:
                    logger.warning(f'Bad device with no ID {device_raw}')
                    continue
                device.id = str(device_id) + '_' + (device_raw.get('name') or '')
                device.hostname = device_raw.get('name')
                ip = device_raw.get('ip')
                try:
                    if ip:
                        device.add_nic(None, ip.split('/'))
                except Exception:
                    logger.exception(f'Problem adding nic to {device_raw}')
                device.domain = device_raw.get('active_directory')
                networks = device_raw.get('networks')
                if isinstance(networks, list):
                    for network in networks:
                        try:
                            ip = network.get('ip_address')
                            if not ip:
                                ips = None
                            else:
                                ips = [ip]
                            mac = network.get('mac_address')
                            if not mac:
                                mac = None
                            if ips or mac:
                                device.add_nic(mac, ips)
                        except Exception:
                            logger.exception(f'Problem adding network to {network}')
                device.description = device_raw.get('description')
                device.device_serial = device_raw.get('serial_number')
                device.device_model = device_raw.get('model')
                try:
                    device.figure_os((device_raw.get('operating_system') or '') + ' ' +
                                     (device_raw.get('operating_system_version') or ''))
                except Exception:
                    logger.exception(f'Problem adding OS to {device_raw}')
                if device_raw.get('username'):
                    device.last_used_users = [device_raw.get('username')]
                try:
                    device.owner = (device_raw.get('owner') or {}).get('name')
                except Exception:
                    logger.exception(f'Probelm getting owner at {device_raw}')
                device.updated_at = parse_date(device_raw.get('updated_at'))
                try:
                    device.department = (device_raw.get('department') or {}).get('name')
                except Exception:
                    logger.exception(f'Problem getting department at {device_raw}')
                try:
                    for software_raw in device_raw.get('software') or []:
                        try:
                            vendor = None
                            vendor_raw = software_raw.get('vendor')
                            if isinstance(vendor_raw, dict):
                                vendor = vendor_raw.get('name')
                            device.add_installed_software(name=software_raw.get('name'),
                                                          version=software_raw.get('version'),
                                                          vendor=vendor)
                        except Exception:
                            logger.exception(f'Problem adding sw to {device_raw}')
                    for software_raw in device_raw.get('hidden_software') or []:
                        try:
                            vendor = None
                            vendor_raw = software_raw.get('vendor')
                            if isinstance(vendor_raw, dict):
                                vendor = vendor_raw.get('name')
                            device.add_installed_software(name=software_raw.get('name'),
                                                          version=software_raw.get('version'),
                                                          vendor=vendor)
                        except Exception:
                            logger.exception(f'Problem adding hidden software to {device_raw}')
                except Exception:
                    logger.exception(f'Problem getting software for {device_raw}')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Samange Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
