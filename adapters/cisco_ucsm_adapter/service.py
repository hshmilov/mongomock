import logging

from urllib3.util import parse_url

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from cisco_ucsm_adapter.connection import CiscoUcsmConnection
from cisco_ucsm_adapter.client_id import get_client_id
from cisco_ucsm_adapter.consts import CLSIDS, BAD_IP, BAD_MAC

logger = logging.getLogger(f'axonius.{__name__}')


class CiscoUcsmAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        vendor = Field(str, 'Device Vendor')
        classid = Field(str, 'Object ClassID')
        distinguished_name = Field(str, 'Distinguished Name')

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
        url_parsed = parse_url(client_config['domain'])
        connection = CiscoUcsmConnection(domain=url_parsed.host,
                                         secure=client_config.get('secure'),
                                         proxy=client_config.get('proxy'),
                                         username=client_config['username'],
                                         password=client_config['password'],
                                         port=client_config.get('port') or None)
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
        The schema CiscoUcsmAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Cisco UCSM IP',
                    'type': 'string'
                },
                {
                    'name': 'port',
                    'title': 'Cisco UCSM Port',
                    'type': 'integer'
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
                    'name': 'secure',
                    'title': 'Secure Connection Supported',
                    'type': 'bool'
                },
                {
                    'name': 'proxy',
                    'title': 'Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'username',
                'password',
                'secure'
            ],
            'type': 'array'
        }

    @staticmethod
    def __add_switch_iface(device, device_raw):
        ips = []
        if device_raw.get('oob_if_ip', BAD_IP) != BAD_IP:
            ips.append(device_raw.get('oob_if_ip', BAD_IP))
        if device_raw.get('inband_if_ip', BAD_IP) != BAD_IP:
            ips.append(device_raw.get('inband_if_ip'))
        mac = device_raw.get('oob_if_mac', BAD_MAC)
        gateway = device_raw.get('oob_if_gw', BAD_IP)
        device.add_nic(
            ips=ips or None,
            mac=mac if mac != BAD_MAC else None,
            gateway=gateway if gateway != BAD_IP else None
        )

    # pylint: disable=W1303, too-many-branches
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('uuid') or device_raw.get('oob_if_mac')
            if not device_id:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            if 'original_uuid' in device_raw:
                secondary_id = device_raw.get('original_uuid')
            else:
                secondary_id = device_raw.get('serial')
            device.id = str(device_id) + '_' + str(secondary_id or 'unnamed')
            device.device_serial = device_raw.get('serial')
            device.device_model = device_raw.get('model')
            device.classid = device_raw.get('class_id')
            device.distinguished_name = device_raw.get('dn')
            if device_raw.get('class_id') == CLSIDS['switch']:
                try:
                    self.__add_switch_iface(device, device_raw)
                except Exception as e:
                    message = f'Could not add interface to switch {device_raw}: {str(e)}'
                    logger.warning(message, exc_info=True)
                    # add the switch anyway
            else:
                props = device_raw.get('ax_props') or {}
                for cpu in props.get('cpus', []):
                    try:
                        device.add_cpu(name=cpu.get('dn'),
                                       manufacturer=cpu.get('vendor'),
                                       cores=int(cpu.get('cores', 0)),
                                       family=cpu.get('arch'),
                                       ghz=float(cpu.get('speed', 0)),
                                       cores_thread=int(cpu.get('threads', 0)))
                    except Exception as e:
                        logger.warning(f'Could not add cpu for {device_raw}: {str(e)}')
                        continue
                for disk in props.get('disks', []):
                    try:
                        descr = '{device_type}:{vendor}_{model}_{serial}_v{version}'.format(disk)
                    except KeyError:
                        descr = None
                    try:
                        device.add_hd(
                            path=disk.get('discovered_path', None),
                            device=disk.get('dn'),
                            total_size=float(disk.get('size', 0)),
                            description=disk.get('fsm_descr') or descr
                        )
                    except Exception as e:
                        logger.warning(f'Could not add hd for {device_raw}: {str(e)}')
                        continue
                for vic in props.get('vics', []):
                    try:
                        device.add_nic(mac=vic.get('base_mac'),
                                       name=vic.get('dn')
                                       )
                    except Exception as e:
                        logger.warning(f'Could not add nic for {device_raw}: {str(e)}')
                        continue
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching CiscoUcsm Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Network]
