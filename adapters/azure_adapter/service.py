import itertools
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


class AzureNetworkSecurityGroupRule(SmartJsonClass):
    iface_name = Field(str, 'Interface Name')
    access = Field(str, 'Access')
    description = Field(str, 'Description')
    direction = Field(str, 'Direction')
    rule_id = Field(str, 'ID')
    name = Field(str, 'Name')
    priority = Field(int, 'Priority')
    protocol = Field(str, 'Protocol')
    source_address_prefixes = ListField(str, 'Source Address Prefixes')
    source_port_ranges = ListField(str, 'Source Port Ranges')
    destination_address_prefixes = ListField(str, 'Destination Address Prefixes')
    destination_port_ranges = ListField(str, 'Destination Port Ranges')
    is_default = Field(bool, 'Is Default')


class AzureAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        account_tag = Field(str, 'Account Tag')
        location = Field(str, 'Azure Location')
        instance_type = Field(str, 'Azure Instance Type')
        image = Field(AzureImage, 'Image')
        admin_username = Field(str, 'Admin Username')
        vm_id = Field(str, 'VM ID')
        azure_firewall_rules = ListField(AzureNetworkSecurityGroupRule, 'Azure Firewall Rules')

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
            metadata_dict = dict()
            if client_config.get('account_tag'):
                metadata_dict['account_tag'] = client_config.get('account_tag')
            return connection, metadata_dict
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
                    'name': 'account_tag',
                    'title': 'Account Tag',
                    'type': 'string'

                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
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

    def _query_devices_by_client(self, client_name, client_data_all):
        client_data, metadata = client_data_all
        return client_data.get_virtual_machines(), metadata

    def _parse_raw_data(self, devices_raw_data_all):
        devices_raw_data, metadata = devices_raw_data_all
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

                try:
                    nsg = iface.get('network_security_group') or {}
                    if not nsg:
                        device.firewall_rules = []
                        device.azure_firewall_rules = []
                    else:
                        for rule, is_default in itertools.chain(
                                zip(nsg.get('security_rules') or [], itertools.repeat(False)),
                                zip(nsg.get('default_security_rules') or [], itertools.repeat(True))
                        ):
                            access = rule.get('access')
                            description = rule.get('description')
                            direction = rule.get('direction')
                            rule_id = rule.get('id')
                            name = rule.get('name')
                            priority = rule.get('Priority')
                            protocol = rule.get('protocol')
                            destination_address_prefix = rule.get('destination_address_prefix')
                            destination_address_prefixes = rule.get('destination_address_prefixes') or []
                            if destination_address_prefix:
                                destination_address_prefixes.append(destination_address_prefix)
                            destination_port_range = rule.get('destination_port_range')
                            destination_port_ranges = rule.get('destination_port_ranges') or []
                            if destination_port_range:
                                destination_port_ranges.append(destination_port_range)

                            source_address_prefix = rule.get('source_address_prefix')
                            source_address_prefixes = rule.get('source_address_prefixes') or []
                            if source_address_prefix:
                                source_address_prefixes.append(source_address_prefix)
                            source_port_range = rule.get('source_port_range')
                            source_port_ranges = rule.get('source_port_ranges') or []
                            if source_port_range:
                                source_port_ranges.append(source_port_range)

                            iface_name = iface.get('name')

                            # First, build the specific rule
                            rule = AzureNetworkSecurityGroupRule(
                                iface_name=iface_name,
                                access=access,
                                description=description,
                                direction=direction,
                                rule_id=rule_id,
                                name=name,
                                priority=priority,
                                protocol=protocol,
                                source_address_prefixes=source_address_prefixes,
                                source_port_ranges=source_port_ranges,
                                destination_address_prefixes=destination_address_prefixes,
                                destination_port_ranges=destination_port_ranges,
                                is_default=is_default
                            )
                            device.azure_firewall_rules.append(rule)

                            # Next, parse the generic rule.
                            # If that is an inbound rule, we care about the source prefix, but destination port.
                            # If that is an outbound rule, we care about the destination prefix, and destination port.
                            port_ranges_to_check = destination_port_ranges
                            if str(direction).lower() == 'inbound':
                                fw_direction = 'INGRESS'
                                address_prefixes_to_check = source_address_prefixes
                            elif str(direction).lower() == 'outbound':
                                fw_direction = 'EGRESS'
                                address_prefixes_to_check = destination_address_prefixes
                            else:
                                logger.error(f'Found unknown direction {str(direction)}, bypassing')
                                continue

                            for address_prefix in address_prefixes_to_check:
                                for port_range in port_ranges_to_check:
                                    if port_range == '*' or str(port_range).lower() == 'all' or \
                                            str(port_range).lower() == 'any':
                                        from_port = 0
                                        to_port = 65535
                                    elif '-' in port_range:
                                        try:
                                            from_port, to_port = port_range.split('-')
                                        except Exception:
                                            from_port, to_port = None, None
                                    else:
                                        try:
                                            from_port, to_port = port_range, port_range
                                        except Exception:
                                            from_port, to_port = None, None

                                    if address_prefix == '*':
                                        address_prefix = '0.0.0.0/0'

                                    if protocol == '*' or str(protocol).lower() == 'all' \
                                            or str(protocol).lower() == 'any':
                                        protocol = 'Any'

                                    device.add_firewall_rule(
                                        name=f'{name} (iface {iface_name})',
                                        source='Azure NIC network security group',
                                        type='Allow' if str(access).lower() == 'allow' else 'Deny',
                                        direction=fw_direction,
                                        target=address_prefix,
                                        protocol=protocol,
                                        from_port=from_port,
                                        to_port=to_port
                                    )

                except Exception:
                    logger.exception(f'Failed to parse network security group, continuing')
            device.account_tag = metadata.get('account_tag')
            device.set_raw(device_raw)
            yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Cloud_Provider]
