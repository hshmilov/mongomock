import logging
import datetime

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from infoblox_adapter.connection import InfobloxConnection

logger = logging.getLogger(f'axonius.{__name__}')


class InfobloxAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        infoblox_network_view = Field(str, 'Network View')
        served_by = Field(str, 'Served By')
        start_time = Field(datetime.datetime, 'Start Time')
        end_time = Field(datetime.datetime, 'End Time')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return client_config['domain']

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def _connect_client(client_config):
        try:
            connection = InfobloxConnection(
                domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
                username=client_config['username'], password=client_config['password'])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific Infoblox domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Infoblox connection

        :return: A json with all the attributes returned from the Infoblox Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema InfobloxAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Infoblox Domain',
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

    # pylint: disable=R0912,R0915
    def _parse_raw_data(self, devices_raw_data):
        ids_set = set()
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                hostname = device_raw.get('client_hostname')
                if hostname:
                    # I did not change hostname to not change ID in many already deployed customers
                    hostname_strip = hostname.strip('"')
                else:
                    hostname_strip = None
                mac_address = device_raw.get('hardware')

                if not hostname and not mac_address:
                    # These devices might not exist, so this log is pretty much spamming.
                    logger.debug(f'No names or mac at : {device_raw}')
                    continue

                try:
                    device.infoblox_network_view = device_raw.get('network_view')
                except Exception:
                    logger.exception(f'can not set network view: {device_raw}')

                device.hostname = hostname_strip
                if mac_address and hostname:
                    device_id = f'mac_{mac_address}_host_{hostname}'
                elif mac_address:
                    device_id = f'mac_{mac_address}'
                elif hostname:
                    device_id = f'host_{hostname}'
                else:
                    logger.error(f'Error - no mac or hostname, can not determine id: {device_raw}, continuing')
                    continue
                if device_id in ids_set:
                    continue
                ids_set.add(device_id)
                device.id = device_id

                ip_address = device_raw.get('address')
                network = device_raw.get('network')

                try:
                    device.add_nic(mac_address,
                                   [ip_address] if ip_address else None,
                                   subnets=[network] if network else None)
                except Exception:
                    logger.exception(f'Can not set nic. device_raw: {device_raw}')

                try:
                    device.served_by = device_raw.get('served_by')
                except Exception:
                    logger.exception(f'Problem getting served by')
                try:
                    start_time = device_raw.get('starts')
                    if start_time:
                        device.start_time = datetime.datetime.fromtimestamp(start_time)
                except Exception:
                    logger.exception(f'Problem getting start time {start_time}')
                try:
                    end_time = device_raw.get('ends')
                    if end_time:
                        device.end_time = datetime.datetime.fromtimestamp(end_time)
                        device.last_seen = datetime.datetime.fromtimestamp(end_time)
                except Exception:
                    logger.exception(f'Problem getting end time {end_time}')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Infoblox Device: {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
