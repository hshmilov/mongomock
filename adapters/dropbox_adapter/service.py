import logging

from dateutil.parser import parse as parse_date

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from dropbox_adapter.client import DropboxConnection

logger = logging.getLogger(f'axonius.{__name__}')


class DropboxAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        carrier = Field(str, 'Mobile Carrier')
        dropbox_client_version = Field(str, 'Client Version')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))
        self.domain = 'https://api.dropboxapi.com/'

    # pylint: disable=R0201
    def _get_client_id(self, client_config):
        """
        :param client_config: client configuration includes access token
        :return:
        """

        return client_config['account_name']

    def _connect_client(self, client_config):
        """
        Creates a Dropbox connection
        :param client_config: client configuration includes generated session from app
        :return: instance of Solarwinds connection
        """

        try:
            connection = DropboxConnection(token=client_config['access_token'], domain=self.domain)
            with connection:
                pass
            return connection
        except Exception as e:
            error_value = self._get_client_id(client_config)
            logger.error(f'Failed to connect to client {error_value}')
            raise ClientConnectionException(str(e))

    # pylint: disable=R0201
    def _query_devices_by_client(self, client_name, session):
        """
        Get a list of all of the devices used by the client
        :param client_name:
        :param session: instance of Dropbox team connection
        :return: device list of the patrolling user's devices
        """
        try:
            with session:
                yield from session.get_device_list()
        except Exception:
            logger.error('There was an exception getting the device list')

    def _test_reachability(self, client_config):
        raise NotImplementedError

    # pylint: disable=R0201
    def _clients_schema(self):
        """
        Denotes the clients schema to be used for the adapter.
        :return:
        """
        return {
            'items': [
                {
                    'name': 'account_name',
                    'title': 'Account Name',
                    'type': 'string'
                },
                {
                    'name': 'access_token',
                    'title': 'Access Token',
                    'type': 'string',
                    'format': 'password',
                }
            ],
            'required': [
                'account_name',
                'access_token'
            ],
            'type': 'array'
        }

    # pylint: disable=R0912
    # pylint: disable=R0915
    def _parse_raw_data(self, raw_data):
        """
        Parses through the raw device list and creates new devices
        to be displayed on the Axonius site.
        :param raw_data: the list of devices that the system patrols
        :return:
        """
        for raw_device_data in iter(raw_data):
            try:
                device = self._new_device_adapter()
                check_for_desktop = raw_device_data.get('host_name', '')
                check_for_mobile = raw_device_data.get('device_name', '')
                client_version = raw_device_data.get('client_version', '')

                # mobile devices have no hostname; desktops have no device_name
                if check_for_desktop:
                    device.id = raw_device_data.get('session_id', '')
                    device.hostname = check_for_desktop
                    device.pc_type = 'Desktop'

                    platform = raw_device_data.get('platform', '')
                    if platform:
                        device.figure_os(platform)
                    logger.info(f'Collected all of the desktop data for {raw_device_data}')

                elif check_for_mobile:
                    device.id = raw_device_data.get('session_id', '')
                    device.name = check_for_mobile
                    device.pc_type = 'Mobile'

                    # attaining client_type.tag because os_version only gives us version number. Client_type
                    # provides us the type of client. ie. os_version = 10.1 and client_type = iPhone. By combining them
                    # the figure_os parser can distinguish that the device is a mac with iOS.
                    os = raw_device_data.get('os_version', '')
                    client_type = raw_device_data.get('client_type', {}).get('.tag', '')
                    os_version = client_type + os
                    if os_version:
                        device.figure_os(os_version)
                    carrier = raw_device_data.get('last_carrier', '')
                    if carrier != 'unavailable' and carrier:
                        device.carrier = carrier
                    device.dropbox_client_version = client_version
                else:
                    logger.error(f'Could not determine if device is desktop or mobile: {raw_device_data}')
                    continue

                # fields common between mobile and desktop devices
                ip_address = raw_device_data.get('ip_address', '')
                device.physical_location = raw_device_data.get('country', '')
                device.set_raw(raw_device_data)
                if ip_address:
                    try:
                        device.add_nic(ips=ip_address.split(','))
                    except Exception:
                        logger.exception(f'Failed parsing the ip address for the device {raw_device_data}')

                try:
                    last_seen = str(raw_device_data.get('updated', ''))
                    if last_seen:
                        date = parse_date(last_seen)
                        device.last_seen = date
                except Exception:
                    logger.exception(f'Parsing the data did not function properly {raw_device_data}')

                logger.info(f'Collected all of the data for {raw_device_data}')

                yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {raw_device_data}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
