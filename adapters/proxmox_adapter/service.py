import logging
from urllib3.util.url import parse_url
from proxmoxer import ProxmoxAPI

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from proxmox_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class ProxmoxAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        vm_status = Field(str, 'VM Status')
        vm_type = Field(str, 'VM Type')
        node_name = Field(str, 'Node Name')

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
            domain = client_config['domain']
            domain = parse_url(domain).host
            ProxmoxAPI(domain, user=client_config['username'],
                       password=client_config['password'], verify_ssl=client_config['verify_ssl'],
                       port=client_config['port']).nodes.get()
            return client_config
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
        domain = client_data['domain']
        domain = parse_url(domain).host
        proxmox = ProxmoxAPI(domain, user=client_data['username'],
                             password=client_data['password'], verify_ssl=client_data['verify_ssl'],
                             port=client_data['port'])
        for resource in proxmox.cluster.resources.get():
            try:
                if resource.get('vmid') and resource.get('type') and resource.get('node'):
                    vm = proxmox.nodes(resource.get('node'))(resource.get('type'))(resource.get('vmid'))
                    yield {'config': vm.config.get(), 'status': vm.status.current.get(),
                           'type': resource.get('type'), 'node': resource.get('node')}
            except Exception:
                logger.exception(f'Problem in resource')

    @staticmethod
    def _clients_schema():
        """
        The schema ProxmoxAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Proxmox Domain',
                    'type': 'string'
                },
                {
                    'name': 'port',
                    'title': 'Port',
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
                'verify_ssl',
                'port'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_status = device_raw.get('status')
                if not device_status.get('vmid'):
                    logger.warning(f'Bad device with no ID {device_raw}')
                    continue
                device.id = device_status.get('vmid') + '_' + device_status.get('name')
                device.name = device_status.get('name')
                device.vm_status = device_status.get('status')
                device.vm_type = device_raw.get('type')
                device.node_name = device_raw.get('node')

                device_config = device_raw.get('config')
                try:
                    net_0 = device_config.get('net0')
                    if net_0 and '=' in net_0.split(',')[0]:
                        device.add_nic(net_0.split(',')[0].split('=')[1], None)
                except Exception:
                    logger.exception(f'Problem adding nic to {device_raw}')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Proxmox Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Virtualization]
