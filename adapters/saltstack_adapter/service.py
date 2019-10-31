import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from saltstack_adapter.connection import SaltstackConnection
from saltstack_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class SaltstackAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        saltversion = Field(str, 'Salt Version')

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
            with SaltstackConnection(domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
                                     eauth=client_config['eauth'],
                                     username=client_config['username'], password=client_config['password'],
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
        The schema SaltstackAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Saltstack Domain',
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
                    'name': 'eauth',
                    'title': 'Eauth',
                    'type': 'string'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                }
            ],
            'required': [
                'domain',
                'username',
                'eauth',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=R0912
    def _parse_raw_data(self, devices_raw_data):
        for node_name, device_raw in devices_raw_data:
            try:
                if not isinstance(device_raw, dict):
                    continue
                device = self._new_device_adapter()
                device.id = node_name + '_' + (device_raw.get('machine_id') or '')
                device.hostname = device_raw.get('fqdn') or device_raw.get()
                try:
                    device.figure_os((device_raw.get('kernel') or '') + ' ' + (device_raw.get('osfullname') or ''))
                except Exception:
                    logger.exception(f'Problem getting os for {device_raw}')
                macs = []
                try:
                    for mac in device_raw.get('hwaddr_interfaces').values():
                        if mac and mac != '00:00:00:00:00:00':
                            macs.append(mac)
                except Exception:
                    logger.exception(f'Problem getting macs for {device_raw}')
                ips = []
                try:
                    for ips_list_name, ips_list in device_raw.get('ip_interfaces').items():
                        if ips_list and ips_list_name != 'lo' and isinstance(ips_list, list):
                            ips.extend(ips_list)
                except Exception:
                    logger.exception(f'Problem getting macs for {device_raw}')
                device.add_ips_and_macs(macs, ips)
                device.device_serial = device_raw.get('serialnumber')
                try:
                    if isinstance(device_raw.get('username'), str):
                        device.last_used_users = device_raw.get('username').split(',')
                except Exception:
                    logger.exception(f'Problem getting users for {device_raw}')
                device.saltversion = device_raw.get('saltversion')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Saltstack Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
