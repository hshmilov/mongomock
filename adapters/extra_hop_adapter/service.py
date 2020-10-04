import logging


from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.devices.device_adapter import DeviceAdapterVlan
from extra_hop_adapter.connection import ExtraHopConnection
from extra_hop_adapter.client_id import get_client_id
from extra_hop_adapter.structures import ExtraHopInstance

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class ExtraHopAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(ExtraHopInstance):
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
        connection = ExtraHopConnection(domain=client_config['domain'],
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
        The schema ExtraHopAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Domain',
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

    @staticmethod
    def _fill_extra_hop_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.mod_time = parse_date(device_raw.get('mod_time'))
            device.node_id = device_raw.get('node_id')
            device.extrahop_id = device_raw.get('extrahop_id')
            device.user_mod_time = parse_date(device_raw.get('user_mod_time'))
            device.parent_id = device_raw.get('parent_id')
            device.vendor = device_raw.get('vendor')
            device.is_l3 = device_raw.get('is_l3')
            device.device_class = device_raw.get('device_class')
            device.default_name = device_raw.get('default_name')
            device.custom_name = device_raw.get('custom_name')
            device.cdp_name = device_raw.get('cdp_name')
            device.netbios_name = device_raw.get('netbios_name')
            device.custom_type = device_raw.get('custom_type')
            device.analysis_level = device_raw.get('analysis_level')
            device.role = device_raw.get('role')
            device.critical = device_raw.get('critical')
            device.display_name = device_raw.get('display_name')

        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            name = device_raw.get('default_name') or device_raw.get('custom_name') or device_raw.get('display_name')
            device.id = str(device_id) + '_' + (name or '')
            device.name = name

            device.device_model = device_raw.get('model')
            device.description = device_raw.get('description')
            device.last_seen = parse_date(device_raw.get('discover_time'))

            netbios_name = device_raw.get('netbios_name')
            hostname = None
            if netbios_name:
                if '\\' in netbios_name:
                    hostname = netbios_name.split('\\')[1]
                else:
                    hostname = netbios_name
            device.hostname = hostname or device_raw.get('cdp_name')

            dns_servers = device_raw.get('dns_name') or []
            if isinstance(dns_servers, str):
                dns_servers = [dns_servers]
            if dns_servers:
                device.dns_servers = dns_servers

            dhcp_servers = device_raw.get('dhcp_name') or []
            if isinstance(dhcp_servers, str):
                dhcp_servers = [dhcp_servers]
            if dhcp_servers:
                device.dhcp_servers = dhcp_servers

            vlans = []
            ips = device_raw.get('ipaddr4') or []
            if isinstance(ips, (str, bytes)):
                ips = [ips]
            if device_raw.get('ipaddr6'):
                ips.extend(device_raw.get('ipaddr6'))
            if device_raw.get('vlanid'):
                vlans = DeviceAdapterVlan()
                vlans.tagid = device_raw.get('vlanid')
                vlans = [vlans]
            device.add_nic(ips=ips,
                           mac=device_raw.get('macaddr'),
                           vlans=vlans)

            self._fill_extra_hop_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching ExtraHop Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            if not device_raw:
                continue
            try:
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching ExtraHop Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
