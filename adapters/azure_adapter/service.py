import logging
logger = logging.getLogger(f'axonius.{__name__}')

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.files import get_local_config_file
from azure_adapter.client import AzureClient


AZURE_SUBSCRIPTION_ID = 'subscription_id'
AZURE_CLIENT_ID = 'client_id'
AZURE_CLIENT_SECRET = 'client_secret'
AZURE_TENANT_ID = 'tenant_id'
AZURE_CLOUD_ENVIRONMENT = 'cloud_environment'


class AzureImage(SmartJsonClass):
    publisher = Field(str, 'Image Publisher')
    offer = Field(str, 'Image Offer')
    sku = Field(str, 'Image SKU')
    version = Field(str, 'Image Version')


class AzureAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        location = Field(str, 'Azure Location')
        instance_type = Field(str, 'Azure Instance Type')
        image = Field(AzureImage, 'Image')
        admin_username = Field(str, 'Admin Username')
        vm_id = Field(str, 'VM ID')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return f'{client_config[AZURE_SUBSCRIPTION_ID]}_{client_config[AZURE_TENANT_ID]}'

    def _test_reachability(self, client_config):
        raise NotImplementedError

    def _connect_client(self, client_config):
        try:
            connection = AzureClient(client_config[AZURE_SUBSCRIPTION_ID],
                                     client_id=client_config[AZURE_CLIENT_ID],
                                     client_secret=client_config[AZURE_CLIENT_SECRET],
                                     tenant_id=client_config[AZURE_TENANT_ID],
                                     cloud_name=client_config.get(AZURE_CLOUD_ENVIRONMENT),
                                     https_proxy=client_config.get('https_proxy'))
            connection.test_connection()
            return connection
        except Exception as e:
            message = "Error connecting to azure with subscription_id {0}, reason: {1}".format(
                client_config[AZURE_SUBSCRIPTION_ID], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": AZURE_SUBSCRIPTION_ID,
                    "title": "Azure Subscription ID",
                    "type": "string"
                },
                {
                    "name": AZURE_CLIENT_ID,
                    "title": "Azure Client ID",
                    "type": "string"
                },
                {
                    "name": AZURE_CLIENT_SECRET,
                    "title": "Azure Client Secret",
                    "type": "string",
                    "format": "password"
                },
                {
                    "name": AZURE_TENANT_ID,
                    "title": "Azure Tenant ID",
                    "type": "string"
                },
                {
                    "name": AZURE_CLOUD_ENVIRONMENT,
                    "title": "Cloud Environment",
                    "type": "string",
                    "enum": list(AzureClient.get_clouds().keys()),
                    "default": AzureClient.DEFAULT_CLOUD
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTP/S Proxy',
                    'type': 'string'
                }
            ],
            "required": [
                AZURE_SUBSCRIPTION_ID,
                AZURE_CLIENT_ID,
                AZURE_CLIENT_SECRET,
                AZURE_TENANT_ID
            ],
            "type": "array"
        }

    def _query_devices_by_client(self, client_name, client_data):
        return client_data.get_virtual_machines()

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._new_device_adapter()
            device.id = device_raw['id']
            device.cloud_id = device_raw['id']
            device.cloud_provider = "Azure"
            device.name = device_raw['name']
            device.location = device_raw.get('location')
            device.instance_type = device_raw.get('hardware_profile', {}).get('vm_size')
            image = device_raw.get('storage_profile', {}).get('image_reference')
            os_disk = device_raw.get('storage_profile', {}).get('os_disk')
            os_info = []
            if os_disk is not None:
                # Add the OS's HD as a hard-drive
                device.add_hd(total_size=os_disk.get('disk_size_gb'))
                os_info.append(os_disk.get('os_type'))
            if image is not None:
                device.image = AzureImage(publisher=image.get('publisher'), offer=image.get('offer'),
                                          sku=image.get('sku'), version=image.get('version'))
                os_info.extend([image.get('offer'), image.get('sku')])
            device.figure_os(' '.join([v for v in os_info if v is not None]))
            for disk in device_raw.get('storage_profile', {}).get('data_disks', []):
                # add also the attached HDs
                device.add_hd(total_size=disk.get('disk_size_gb'))
            device.hostname = device_raw.get('os_profile', {}).get('computer_name')
            device.admin_username = device_raw.get('os_profile', {}).get('admin_username')
            device.vm_id = device_raw.get('vm_id')
            for iface in device_raw.get('network_profile', {}).get('network_interfaces', []):
                ips = []
                subnets = []
                for ip_config in iface.get('ip_configurations', []):
                    private_ip = ip_config.get('private_ip_address')
                    if private_ip:
                        ips.append(private_ip)
                    public_ip = ip_config.get('public_ip_address', {}).get('ip_address')
                    if public_ip:
                        ips.append(public_ip)
                        device.add_public_ip(public_ip)
                    subnets.append(ip_config.get('subnet', {}).get('address_prefix'))
                device.add_nic(mac=iface.get('mac_address'), ips=[ip for ip in ips if ip is not None],
                               subnets=[subnet for subnet in subnets if subnet is not None], name=iface.get('name'))
            device.set_raw(device_raw)
            yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Cloud_Provider]
